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
    ~ParseDaemon();

    bool parseOneSourceById(int sourceId, QString* errorOut = nullptr);
    bool setSourceStatus(int sourceId, const QString& status);

    void start();

private slots:
    void tick();
    void parceSources(const QList<QVariantMap>& sources);
    bool parseOneSourceWithParser(class feedpp::parser& p,
                                  const QVariantMap& src,
                                  QString* errorOut);

    QString languageCheck(QStringView text);
    friend QDateTime parsePublishedAtUtc(const struct feedpp::item& it);
private:
    QTimer timer;
    DBManager DBMg;
};
