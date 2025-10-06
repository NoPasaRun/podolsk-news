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

class LlmTopics;
#include "llm_topics.hpp"
#include "topics_enum.hpp"

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
    void classifyNewClustersSingle(const QVector<ArticleInsertResult>& results,
                                   const QList<QVariantMap>& rows,
                                   const QString& lang);
private:
    QTimer timer;
    DBManager DBMg;
    LlmTopics* llmTopics_ = nullptr;

    QStringList topicLabels_;
    QHash<QString,int> topicKeyToId_;

    static QString normKey(const QString& s);
    
};
