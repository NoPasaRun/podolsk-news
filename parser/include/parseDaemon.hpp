#pragma once

#include <QObject>
#include <QTimer>
#include <vector>
#include <string>
#include <QDate>
#include "feedpp.h"  
#include "databaseManager.hpp"
#include <QList>
#include <QChar>
#include <QString>
#include <QVariantMap>

struct Source {
    int id;
    std::string url;
};

class ParseDaemon : public QObject {
    Q_OBJECT

public:
    explicit ParseDaemon(QObject* parent = nullptr);
    QString languageCheck(QString text);
    void parceSources(const QList<QVariantMap> &sources);
    ~ParseDaemon();

    void start();

private slots:
    void tick();

private:
    QTimer timer;
    DBManager DBMg;
};
