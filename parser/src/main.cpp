#include <QCoreApplication>
#include "parseDaemon.hpp"

int main(int argc, char* argv[]) {
    QCoreApplication app(argc, argv);


    std::setlocale(LC_TIME, "C");
    ParseDaemon daemon;
    daemon.start();

    return app.exec();
}
