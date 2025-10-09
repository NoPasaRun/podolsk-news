#include <QCoreApplication>
#include "parseDaemon.hpp"
#include "react_service.hpp"
#include <QDebug>
#include <QThread>


int main(int argc, char* argv[]) {
    QCoreApplication app(argc, argv);
    std::setlocale(LC_TIME, "C");

    auto* daemon = new ParseDaemon("pg_conn_thread");
    auto* check_daemon = new ParseDaemon("pg_conn_main");
    auto* daemonThread = new QThread(&app);
    daemon->moveToThread(daemonThread);

    QObject::connect(daemonThread, &QThread::started, daemon, &ParseDaemon::start);
    QObject::connect(&app, &QCoreApplication::aboutToQuit, daemon, &ParseDaemon::stop);
    QObject::connect(daemonThread, &QThread::finished, daemon, &QObject::deleteLater);

    daemonThread->start();

    const QString redisUrl   = qEnvironmentVariable("REDIS_URL",        "redis://redis:6379/0");
    const QString inChannel  = qEnvironmentVariable("RSS_IN_CHANNEL",   "rss_news_fetch_requests");
    const QString outChannel = qEnvironmentVariable("REDIS_OUT_CHANNEL","news_fetch_results");

	check_daemon->openDB();
    ReactService svc(*check_daemon, redisUrl, inChannel, outChannel);
	svc.start();

    return app.exec();
}
