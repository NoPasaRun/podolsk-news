#pragma once

#include <QtSql/QSqlDatabase>
#include <QtSql/QSqlQuery>
#include <QtSql/QSqlError>
#include <QString>
#include <QVariant>
#include <vector>
#include <string>
#include "config.hpp"

class DBManager {
public:
    DBManager(const QString& driver = "QPSQL");
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
    void insertDemoSource();

    QVariantMap getSourceById(int id);
    bool updateSourceStatus(int id, const QString& status);

    bool bumpSourcesLastUpdatedRange(int idFrom, int idTo, const QDateTime &ts);

    QVector<int> insertArticles(const QList<QVariantMap> &rows);
    // QVector<int> upsertArticlesBatch(const QList<QVariantMap> &rows);
    // void insertArticle(const QString &url, const QString &urlCanon, const QString &title, const QString &summary, const QString &contentHtml, const QDateTime &publishedAt, const QString &language, const QString &contentFingerprint, int clusterId, int sourceId);
    QList<QVariantMap> listRssSourcesRange(int idFrom, int idTo);

    Config config;

private:
    QSqlDatabase db;
   
};
