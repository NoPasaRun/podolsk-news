#include "react_service.hpp"

#include <QJsonDocument>
#include <QJsonObject>
#include <QUrl>
#include <QDebug>

#include "parseDaemon.hpp"
#include "redis_subscriber.hpp"
#include <sw/redis++/redis++.h>

// Преобразование redis://host:port/db в ConnectionOptions (без TLS)
sw::redis::ConnectionOptions ReactService::makeConnOptsFromUri(const QString& uri) {
    sw::redis::ConnectionOptions opts;
    QUrl u(uri);
    if (u.isValid() && (u.scheme() == "redis" || u.scheme() == "rediss")) {
        opts.host = u.host().toStdString();
        opts.port = static_cast<int>(u.port(6379));
        QString path = u.path();
        if (path.startsWith('/')) path = path.mid(1);
        bool ok=false; int db = path.toInt(&ok);
        if (ok) opts.db = db;
        if (!u.password().isEmpty()) opts.password = u.password().toStdString();
        // Для TLS (rediss) нужна сборка redis++ с TLS и hiredis_ssl; здесь предполагаем без TLS.
    } else {
        opts.host = "127.0.0.1"; opts.port = 6379; opts.db = 0;
    }
    // Делаем consume() периодическим (TimeoutError), чтобы иметь шанс аккуратно выйти
    opts.socket_timeout = std::chrono::milliseconds(2000);
    return opts;
}

ReactService::ReactService(ParseDaemon& daemon,
                           QString redisUrl,
                           QString inChannel,
                           QString outChannel,
                           QObject* parent)
    : QObject(parent)
    , daemon_(daemon)
    , redisUrl_(std::move(redisUrl))
    , inChan_(std::move(inChannel))
    , outChan_(std::move(outChannel))
{}

ReactService::~ReactService() {
    if (sub_) { sub_->deleteLater(); sub_ = nullptr; }
    delete pub_; pub_ = nullptr;
}

bool ReactService::start() {
    // Publisher
    try {
        auto opts = makeConnOptsFromUri(redisUrl_);
        pub_ = new sw::redis::Redis(opts);
    } catch (const std::exception& e) {
        qWarning() << "[ReactService] Redis publisher init failed:" << e.what();
        return false;
    }

    // Subscriber
    sub_ = new RedisSubscriber(redisUrl_, {inChan_});
    connect(sub_, &RedisSubscriber::message,      this, &ReactService::onRedisMessage);
    connect(sub_, &RedisSubscriber::connected,   []{ qInfo()  << "[ReactService] subscriber connected"; });
    connect(sub_, &RedisSubscriber::disconnected,[](const QString& why){ qWarning() << "[ReactService] subscriber disconnected:" << why; });

    sub_->setReconnectDelay(200, 2000);
    sub_->start();

    emit started();
    return true;
}

void ReactService::onRedisMessage(const QString& channel, const QByteArray& payload) {
    Q_UNUSED(channel);
    qWarning() << "[ReactService] received message";

    const auto doc = QJsonDocument::fromJson(payload);
    if (!doc.isObject()) {
        qWarning() << "[ReactService] bad payload (not JSON object):" << payload;
        publishStatus(-1, -1, "error", "bad_payload");
        return;
    }

    const auto obj = doc.object();
    const int sourceId = obj.value("source_id").toInt(-1);
    const int userId   = obj.value("user_id").toInt(-1);

    if (sourceId <= 0 || userId <= 0) {
        qWarning() << "[ReactService] bad fields in payload:" << payload;
        publishStatus(sourceId, userId, "error", "bad_payload_fields");
        return;
    }

    // дергаем существующую логику демона — БЕЗ дублирования кода
    QString err;
    const bool ok = daemon_.parseOneSourceById(sourceId, &err);

    if (ok) {
        daemon_.setSourceStatus(sourceId, "active");
        publishStatus(sourceId, userId, "active");
    } else {
        daemon_.setSourceStatus(sourceId, "error");
        publishStatus(sourceId, userId, "error", err);
    }
}

bool ReactService::publishStatus(int sourceId, int userId, const QString& status, const QString& errorText) {
    if (!pub_) return false;

    QJsonObject out{
        {"source_id", sourceId},
        {"user_id",   userId},
        {"status",    status}
    };
    if (!errorText.isEmpty())
        out.insert("error", errorText);

    const QByteArray json = QJsonDocument(out).toJson(QJsonDocument::Compact);

    try {
        pub_->publish(outChan_.toStdString(), std::string(json.constData(), json.size()));
        return true;
    } catch (const std::exception& e) {
        qWarning() << "[ReactService] publish error:" << e.what();
        return false;
    }
}
