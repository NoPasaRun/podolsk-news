#pragma once
#include <QObject>
#include <QString>

class ParseDaemon;
class RedisSubscriber;

namespace sw { namespace redis {
    class Redis;
    struct ConnectionOptions;
}}

/**
 * ReactService — сервис-оркестратор:
 *  - слушает входной Redis-канал с командами
 *  - по команде парсит один источник через ParseDaemon
 *  - шлёт ответ в выходной канал и обновляет статус источника в БД
 */
class ReactService : public QObject {
    Q_OBJECT
public:
    explicit ReactService(ParseDaemon& daemon,
                          QString redisUrl,
                          QString inChannel,
                          QString outChannel,
                          QObject* parent = nullptr);
    ~ReactService() override;

    // Инициализация: проверяет БД через daemon, настраивает Redis pub/sub и запускает подписчик
    bool start();

signals:
    void started();

private slots:
    // Сообщение из входного канала: payload = JSON {source_id, user_id}
    void onRedisMessage(const QString& channel, const QByteArray& payload);

private:
    // Публикация статуса в выходной канал
    bool publishStatus(int sourceId, int userId, const QString& status, const QString& errorText = {});

    // Разбор redis:// URI в redis++ ConnectionOptions (без TLS)
    static sw::redis::ConnectionOptions makeConnOptsFromUri(const QString& uri);

private:
    ParseDaemon& daemon_;

    QString redisUrl_;
    QString inChan_;
    QString outChan_;

    RedisSubscriber*   sub_ = nullptr;   // подписчик (наш модуль)
    sw::redis::Redis*  pub_ = nullptr;   // издатель (redis++)
};
