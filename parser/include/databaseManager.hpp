#pragma once

#include <QtSql/QSqlDatabase>
#include <QtSql/QSqlQuery>
#include <QtSql/QSqlError>
#include <QString>
#include <QVariant>
#include <vector>
#include <string>
#include "config.hpp"

struct ArticleInsertResult {
    int   clusterId = 0;
    int   articleId = 0;
    double score    = 0.0;
    bool  matched   = false;
    bool  createdNew= false;
};

class DBManager {
public:
    DBManager(const QString& conn_name, const QString& driver = "QPSQL");
    ~DBManager();


    bool open();
    void close();
    bool isOpen() const;
    void dbCheck();

    bool exec(const QString& queryStr);

    // выборка (возвращаем вектор строк)
    std::vector<std::vector<QVariant>> select(const QString& queryStr);
    QString getGlobalSourcesJson();

    void demoData();
    void insertDemoSource() ;

    QVariantMap getSourceById(int id);
    bool updateSourceStatus(int id, const QString& status);

    bool bumpSourcesLastUpdatedRange(int idFrom, int idTo, const QDateTime &ts);

    QVector<ArticleInsertResult> insertArticles(const QList<QVariantMap>& rows);
    QList<QVariantMap> listRssSourcesRange(int idFrom, int idTo);

    QList<QVariantMap> getClusterArticles(int clusterId, int limit) const;
    int  ensureTopic(const QString& title); // создаст при отсутствии и вернёт id
    bool upsertClusterTopic(int clusterId, int topicId, double score, bool primary);
    bool clearClusterPrimary(int clusterId);

    Config config;

private:
    QSqlDatabase db;
   	void ensureTopicTitleUniqueIndex();
};
