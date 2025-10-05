#include <QCoreApplication>
#include "parseDaemon.hpp"
#include "react_service.hpp"


int main(int argc, char* argv[]) {
    QCoreApplication app(argc, argv);
    std::setlocale(LC_TIME, "C");

    ParseDaemon daemon;
    daemon.start();

    const QString redisUrl   = qEnvironmentVariable("REDIS_URL",        "redis://redis:6379/0");
    const QString inChannel  = qEnvironmentVariable("REDIS_IN_CHANNEL", "news_fetch_requests");
    const QString outChannel = qEnvironmentVariable("REDIS_OUT_CHANNEL","news_fetch_results");

    ReactService svc(daemon, redisUrl, inChannel, outChannel);
    if (!svc.start()) return 1;

    return app.exec();
}

#include "main.moc"
