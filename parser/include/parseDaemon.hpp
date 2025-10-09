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

class TopicAssigner;

class ParseDaemon : public QObject {
    Q_OBJECT

public:
    explicit ParseDaemon(const QString& conn_name, QObject* parent = nullptr);
    ~ParseDaemon();

    bool parseOneSourceById(int sourceId, QString* errorOut = nullptr);
    bool setSourceStatus(int sourceId, const QString& status);

public slots:
	void start();
	void stop();
	void openDB();
private slots:
    void tick();
    void parceSources(const QList<QVariantMap>& sources);
    bool parseOneSourceWithParser(class feedpp::parser& p,
                                  const QVariantMap& src,
                                  QString* errorOut);

    QString languageCheck(QStringView text);
    friend QDateTime parsePublishedAtUtc(const struct feedpp::item& it);
private:
    DBManager DBMg;
    QTimer* timer_ = nullptr;
    TopicAssigner* topicAssigner = nullptr;
};
