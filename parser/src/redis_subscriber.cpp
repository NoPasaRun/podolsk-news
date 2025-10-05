#include "redis_subscriber.hpp"
#include <QThread>
#include <QDebug>
#include <QUrl>
#include <atomic>
#include <memory>
#include <chrono>
#include <random>
#include <utility>

#include <sw/redis++/redis++.h>

using namespace std::chrono_literals;

static sw::redis::ConnectionOptions makeConnOptsFromUri(const QString& uri) {
    sw::redis::ConnectionOptions opts;
    QUrl u(uri);
    if (u.isValid() && (u.scheme() == "redis" || u.scheme() == "rediss")) {
        // host/port
        opts.host = u.host().toStdString();
        opts.port = static_cast<int>(u.port(6379));
        // db из пути: /0
        QString path = u.path();
        if (path.startsWith('/')) path = path.mid(1);
        bool ok = false;
        int db = path.toInt(&ok);
        if (ok) opts.db = db;
        // password
        if (!u.password().isEmpty()) opts.password = u.password().toStdString();
        // NOTE: если нужен TLS (rediss), собирай redis++ с TLS и hiredis_ssl.
        // Здесь мы просто игнорируем TLS-флаги, т.к. сборка без TLS.
    } else {
        // Фоллбек: redis://localhost:6379/0
        opts.host = "127.0.0.1";
        opts.port = 6379;
        opts.db   = 0;
    }
    // Таймаут сокета, чтобы consume() периодически «прокидывал» TimeoutError
    opts.socket_timeout = std::chrono::milliseconds(2000);
    return opts;
}

class RedisSubscriber::Worker : public QObject {
    Q_OBJECT
public:
    explicit Worker(QString url, QStringList ch, QStringList pat, QObject* parent=nullptr)
        : QObject(parent), url_(std::move(url)), channels_(std::move(ch)), patterns_(std::move(pat)) {}

    void setReconnectRange(int minMs, int maxMs) {
        minDelayMs_ = std::max(10, minMs);
        maxDelayMs_ = std::max(minDelayMs_, maxMs);
    }

public slots:
    void start() {
        running_.store(true);
        loop();
    }

    void stop() {
        running_.store(false);
        // Ничего не делаем: consume() вернёт TimeoutError по socket_timeout и цикл выйдет
    }

    void subscribe(const QString& ch)   { pendingSubs_    << ch; }
    void unsubscribe(const QString& ch) { pendingUnsubs_  << ch; }
    void psubscribe(const QString& pt)  { pendingPSubs_   << pt; }
    void punsubscribe(const QString& pt){ pendingPUnsubs_ << pt; }

signals:
    void connected();
    void disconnected(const QString& reason);
    void message(const QString& channel, const QByteArray& payload);
    void error(const QString& what);
    void finished();

private:
    void loop() {
        std::mt19937 rng{std::random_device{}()};
        while (running_.load()) {
            try {
                auto opts = makeConnOptsFromUri(url_);
                sw::redis::Redis redis(opts);

                sub_ = std::make_unique<sw::redis::Subscriber>(redis.subscriber());

                sub_->on_message([this](std::string chan, std::string msg) {
                    emit message(QString::fromStdString(chan),
                                 QByteArray(msg.data(), static_cast<int>(msg.size())));
                });
                // on_error не у всех версий есть — ошибки ловим через исключения ниже

                for (const auto& c : channels_)  sub_->subscribe(c.toStdString());
                for (const auto& p : patterns_)  sub_->psubscribe(p.toStdString());

                emit connected();

                while (running_.load()) {
                    flushPending();
                    try {
                        sub_->consume(); // блокируется до события/таймаута
                    } catch (const sw::redis::TimeoutError&) {
                        // нормальный сценарий — даёт шанс выйти по stop()
                    } catch (const std::exception& e) {
                        emit error(QString::fromUtf8(e.what()));
                        throw; // выкинем наверх, чтобы реконнектнуться
                    }
                }
            } catch (const std::exception& e) {
                emit disconnected(QString::fromUtf8(e.what()));
                // backoff перед реконнектом
                std::uniform_int_distribution<int> dist(minDelayMs_, maxDelayMs_);
                int ms = dist(rng);
                for (int slept=0; running_.load() && slept < ms; ) {
                    QThread::msleep(100);
                    slept += 100;
                }
            }
            sub_.reset();
        }
        emit finished();
    }

    void flushPending() {
        if (!sub_) return;

        for (const auto& c : std::exchange(pendingSubs_, {})) {
            try { sub_->subscribe(c.toStdString()); } catch (const std::exception& e) {
                emit error(QString("subscribe(%1): %2").arg(c, e.what()));
            }
        }
        for (const auto& c : std::exchange(pendingUnsubs_, {})) {
            try { sub_->unsubscribe(c.toStdString()); } catch (const std::exception& e) {
                emit error(QString("unsubscribe(%1): %2").arg(c, e.what()));
            }
        }
        for (const auto& p : std::exchange(pendingPSubs_, {})) {
            try { sub_->psubscribe(p.toStdString()); } catch (const std::exception& e) {
                emit error(QString("psubscribe(%1): %2").arg(p, e.what()));
            }
        }
        for (const auto& p : std::exchange(pendingPUnsubs_, {})) {
            try { sub_->punsubscribe(p.toStdString()); } catch (const std::exception& e) {
                emit error(QString("punsubscribe(%1): %2").arg(p, e.what()));
            }
        }
    }

    QString url_;
    QStringList channels_;
    QStringList patterns_;
    std::unique_ptr<sw::redis::Subscriber> sub_;
    std::atomic_bool running_{false};
    int minDelayMs_ = 500;
    int maxDelayMs_ = 5000;

    QStringList pendingSubs_, pendingUnsubs_, pendingPSubs_, pendingPUnsubs_;
};

RedisSubscriber::RedisSubscriber(QString url, QStringList channels, QStringList patterns, QObject* parent)
    : QObject(parent)
{
    worker_ = new Worker(std::move(url), std::move(channels), std::move(patterns));
    thread_ = new QThread(this);
    worker_->moveToThread(thread_);

    QObject::connect(thread_,  &QThread::started, worker_, &Worker::start);
    QObject::connect(this,     &RedisSubscriber::destroyed, worker_, &Worker::stop);
    QObject::connect(worker_,  &Worker::finished, thread_, &QThread::quit);
    QObject::connect(worker_,  &Worker::finished, worker_, &QObject::deleteLater);
    QObject::connect(thread_,  &QThread::finished, thread_, &QObject::deleteLater);

    QObject::connect(worker_, &Worker::connected,    this, &RedisSubscriber::connected);
    QObject::connect(worker_, &Worker::disconnected, this, &RedisSubscriber::disconnected);
    QObject::connect(worker_, &Worker::message,      this, &RedisSubscriber::message);
    QObject::connect(worker_, &Worker::error,        this, &RedisSubscriber::error);
}

RedisSubscriber::~RedisSubscriber() {
    stop();
    if (thread_ && thread_->isRunning()) {
        thread_->quit();
        thread_->wait(2000);
    }
}

void RedisSubscriber::setReconnectDelay(int minMs, int maxMs) {
    QMetaObject::invokeMethod(worker_, [this,minMs,maxMs]{ worker_->setReconnectRange(minMs, maxMs); },
                              Qt::QueuedConnection);
}
void RedisSubscriber::start() { if (thread_ && !thread_->isRunning()) thread_->start(); }
void RedisSubscriber::stop()  { if (worker_) QMetaObject::invokeMethod(worker_, &Worker::stop, Qt::QueuedConnection); }

void RedisSubscriber::subscribe(const QString& c)   { QMetaObject::invokeMethod(worker_, "subscribe",   Qt::QueuedConnection, Q_ARG(QString, c)); }
void RedisSubscriber::unsubscribe(const QString& c) { QMetaObject::invokeMethod(worker_, "unsubscribe", Qt::QueuedConnection, Q_ARG(QString, c)); }
void RedisSubscriber::psubscribe(const QString& p)  { QMetaObject::invokeMethod(worker_, "psubscribe",  Qt::QueuedConnection, Q_ARG(QString, p)); }
void RedisSubscriber::punsubscribe(const QString& p){ QMetaObject::invokeMethod(worker_, "punsubscribe", Qt::QueuedConnection, Q_ARG(QString, p)); }

#include "redis_subscriber.moc"
