#include "databaseManager.hpp"
#include <QDebug>

DBManager::DBManager(const QString& driver) {
    db = QSqlDatabase::addDatabase(driver, "pg_conn");
    
}

DBManager::~DBManager() {
    if (db.isOpen()) {
        db.close();
    }
}

void DBManager::dbCheck()
{
    if (!db.isOpen()) {
        qWarning() << "DB not open";
        return;
    }
}

bool DBManager::open() {
    
    unsetenv("PGHOST"); qunsetenv("PGPORT"); qunsetenv("PGDATABASE");
    qunsetenv("PGUSER"); qunsetenv("PGPASSWORD"); qunsetenv("PGSERVICE");

    config.parse("res/config.json");

    db.setHostName(config.db_address);
    db.setPort(config.db_port);
    db.setDatabaseName(config.db_name);
    db.setUserName(config.db_user);
    db.setPassword(config.db_password);

    db.setConnectOptions("connect_timeout=5");


    qDebug() << "Drivers:" << QSqlDatabase::drivers();
    qDebug() << "About to connect:"
             << "host=" << db.hostName()
             << "port=" << db.port()
             << "db="   << db.databaseName()
             << "user=" << db.userName();

    if (!db.open()) {
        qWarning() << "DB open error:" << db.lastError().text();
        return false;
    }
    else 
    {
        qDebug() << "db connect OK";

    }

    return true;
}

void DBManager::close() {
    if (db.isOpen())
        db.close();
}

bool DBManager::isOpen() const {
    return db.isOpen();
}

bool DBManager::exec(const QString& queryStr) {
    QSqlQuery query(db);
    if (!query.exec(queryStr)) {
        qWarning() << "Query error:" << query.lastError().text();
        return false;
    }
    return true;
}

QList<QVariantMap> DBManager::listRssSourcesRange(int idFrom, int idTo) {
    dbCheck();
    QList<QVariantMap> out;
    if (idTo < idFrom) std::swap(idFrom, idTo);

    QSqlQuery q(db);
    q.prepare(R"SQL(
        SELECT id, domain, last_updated_at
        FROM public.source
        WHERE kind = 'rss' AND status IN ('validating','verified')
          AND id BETWEEN :from AND :to
        ORDER BY id ASC
    )SQL");
    q.bindValue(":from", idFrom);
    q.bindValue(":to",   idTo);

    if (!q.exec()) {
        qWarning() << "listRssSourcesRange failed:" << q.lastError().text();
        return out;
    }
    while (q.next()) {
        QVariantMap row;
        row["id"]              = q.value(0).toInt();
        row["domain"]          = q.value(1).toString();
        row["last_updated_at"] = q.value(2).toDateTime();
        out.append(row);
    }
    return out;
}

   

QVector<int> DBManager::insertArticles(const QList<QVariantMap>& rows) {
    dbCheck();
    QVector<int> ids; ids.reserve(rows.size());
    if (rows.isEmpty()) return ids;

    if (!db.transaction()) {
        qWarning() << "tx begin failed:" << db.lastError().text();
    }

    QSqlQuery q(db);
        q.prepare(R"SQL(
        INSERT INTO public.article
            (url, title, summary, published_at,
             language, content_fingerprint, cluster_id, source_id)
        VALUES
            (:url, :title, :summary, :published_at,
             :language, :content_fingerprint, :cluster_id, :source_id)
    
        ON CONFLICT DO NOTHING
        RETURNING id
    )SQL");


    for (const auto& r : rows) {
        q.bindValue(":url",                 r.value("url"));
        q.bindValue(":title",               r.value("title"));
        q.bindValue(":summary",             r.value("summary"));
        q.bindValue(":published_at",        r.value("published_at"));      // QDateTime
        q.bindValue(":language",            r.value("language"));
        q.bindValue(":content_fingerprint", "[хуйгерпринт]");
        q.bindValue(":cluster_id",          228);        
        q.bindValue(":source_id",           r.value("source_id"));          // укажи ниже в tick()
            

        if (!q.exec()) {
            qWarning() << "Insert article failed:" << q.lastError().text();
            db.rollback();
            return {};
        }
        else
        {
            qDebug() << "insert good";
        }
    
    
    if (q.next()) ids.push_back(q.value(0).toInt()); // будет пусто если конфликт и DO NOTHING
        q.finish(); // очистить перед следующим биндингом
    }

    if (!db.commit()) {
        qWarning() << "commit failed:" << db.lastError().text();
    }
    return ids;
}






void DBManager::demoData()
{
    insertDemoSource();
}

void DBManager::insertDemoSource() {
    dbCheck();

   QStringList inserts = {

        // 1) placeholder-кластер (id=228)
        R"SQL(
        INSERT INTO public.cluster (id, title, summary, top_image, first_published_at, language, weight)
        VALUES
        (228, 'unclustered', 'temporary placeholder cluster', NULL, NOW(), 'auto', 0)
        ON CONFLICT (id) DO NOTHING
        )SQL",

        // 2) источник (не падаем на повторах)
        R"SQL(
        INSERT INTO public.source (kind, domain, status)
        VALUES ('rss','https://www.vedomosti.ru/rss/news.xml','validating')
        ON CONFLICT (kind, domain) DO NOTHING
        )SQL",

        // 3) TASS
        R"SQL(
        INSERT INTO public.source (kind, domain, status)
        VALUES ('rss','https://tass.ru/rss/v2.xml','validating')
        ON CONFLICT (kind, domain) DO NOTHING
        )SQL",

        // 4) RBC
        R"SQL(
        INSERT INTO public.source (kind, domain, status)
        VALUES ('rss','https://rssexport.rbc.ru/rbcnews/news/30/full.rss','validating')
        ON CONFLICT (kind, domain) DO NOTHING
        )SQL",

        // 5) The Guardian
        R"SQL(
        INSERT INTO public.source (kind, domain, status)
        VALUES ('rss','https://www.theguardian.com/world/rss','validating')
        ON CONFLICT (kind, domain) DO NOTHING
        )SQL"
    };

    for (const QString& sql : inserts) {
        QSqlQuery q(db);
        if (!q.exec(sql)) {
            qWarning() << "Insert failed:" << q.lastError().text();
            continue;
        }
        if (q.next()) {
            qDebug() << "Inserted id =" << q.value(0).toInt();
        }
    }
    
}


bool DBManager::bumpSourcesLastUpdatedRange(int idFrom, int idTo, const QDateTime& ts) {
    dbCheck();
    if (idTo < idFrom) std::swap(idFrom, idTo);

    QSqlQuery q(db);
    q.prepare(R"SQL(
        UPDATE public.source
        SET last_updated_at = :ts
        WHERE id BETWEEN :from AND :to
    )SQL");
    q.bindValue(":ts", ts);
    q.bindValue(":from", idFrom);
    q.bindValue(":to",   idTo);

    if (!q.exec()) {
        qWarning() << "bumpSourcesLastUpdatedRange failed:" << q.lastError().text();
        return false;
    }
    return true;
}