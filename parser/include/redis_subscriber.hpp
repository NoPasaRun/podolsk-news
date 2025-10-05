#pragma once
#include <QObject>
#include <QString>
#include <QStringList>

class QThread;

class RedisSubscriber : public QObject {
    Q_OBJECT
public:
    explicit RedisSubscriber(QString url,
                             QStringList channels = {},
                             QStringList patterns = {},
                             QObject* parent = nullptr);
    ~RedisSubscriber() override;

    // Диапазон бэкоффа при реконнекте (мс)
    void setReconnectDelay(int minMs, int maxMs);

public slots:
    void start();
    void stop();

    // Динамические подписки (выполняются в воркере)
    void subscribe(const QString& channel);
    void unsubscribe(const QString& channel);
    void psubscribe(const QString& pattern);
    void punsubscribe(const QString& pattern);

signals:
    void connected();
    void disconnected(const QString& reason);
    void message(const QString& channel, const QByteArray& payload);
    void error(const QString& what);

private:
    class Worker;
    Worker* worker_ = nullptr;
    QThread* thread_ = nullptr;
};
