#include "databaseManager.hpp"
#include <QRegularExpression>
#include <QDebug>

DBManager::DBManager(const QString& conn_name, const QString& driver) {
    db = QSqlDatabase::addDatabase(driver, conn_name);
    
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

void DBManager::ensureTopicTitleUniqueIndex() {
    QSqlQuery q(db);
    // делаем title уникальным, чтобы не плодить записи
    // если индекс уже есть — ошибок не будет
    q.exec(R"SQL(
        DO $$
        BEGIN
            IF NOT EXISTS (
                SELECT 1
                FROM pg_indexes
                WHERE schemaname = 'public'
                  AND indexname = 'idx_topic_title_unique'
            ) THEN
                CREATE UNIQUE INDEX idx_topic_title_unique ON public.topic (title);
            END IF;
        END$$;
    )SQL");
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
		ensureTopicTitleUniqueIndex();
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
        WHERE kind = 'rss' AND status IN ('active')
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

   

QVector<ArticleInsertResult> DBManager::insertArticles(const QList<QVariantMap>& rows) {
    dbCheck();
    QVector<ArticleInsertResult> results; results.reserve(rows.size());
    if (rows.isEmpty()) return results;

    if (!db.transaction()) {
        qWarning() << "[insertArticles] tx begin failed:" << db.lastError().text();
        return {};
    }

    QSqlQuery q(db);
    q.prepare(R"SQL(
        SELECT
            out_cluster_id,
            out_article_id,
            out_score,
            out_matched,
            out_created_new
        FROM upsert_article_with_cluster(
            p_source_id     => :p_source_id,
            p_url           => :p_url,
            p_title         => :p_title,
            p_image         => :p_image,
            p_summary       => :p_summary,
            p_published_at  => :p_published_at,
            p_language      => :p_language,
            p_recency       => '1 hour',
            p_min_score     => 0.2
        )
    )SQL");

    for (const auto& r : rows) {
        q.bindValue(":p_source_id",  r.value("source_id"));
        q.bindValue(":p_url",        r.value("url"));
        q.bindValue(":p_title",      r.value("title"));

        if (r.contains("url_image") && !r.value("url_image").isNull())
            q.bindValue(":p_image", r.value("url_image"));
        else
            q.bindValue(":p_image", QVariant(QVariant::String));

        if (r.contains("summary") && !r.value("summary").isNull())
            q.bindValue(":p_summary", r.value("summary"));
        else
            q.bindValue(":p_summary", QVariant(QVariant::String));

        q.bindValue(":p_published_at",  r.value("published_at").toDateTime());

        if (r.contains("language") && !r.value("language").isNull())
            q.bindValue(":p_language", r.value("language"));
        else
            q.bindValue(":p_language", QVariant("auto"));

        if (!q.exec()) {
            qWarning() << "[insertArticles] upsert_article_with_cluster failed:"
                       << q.lastError().text()
                       << "url=" << r.value("url");
            db.rollback();
            return {};
        }
        if (!q.next()) {
            qWarning() << "[insertArticles] no row returned for url=" << r.value("url");
            q.finish();
            db.rollback();
            return {};
        }

        ArticleInsertResult one;
        one.clusterId  = q.value(0).toInt();
        one.articleId  = q.value(1).toInt();
        one.score      = q.value(2).toDouble();
        one.matched    = q.value(3).toBool();
        one.createdNew = q.value(4).toBool();
        results.push_back(one);

        q.finish();
    }

    if (!db.commit()) {
        qWarning() << "[insertArticles] commit failed:" << db.lastError().text();
        return {};
    }
    return results;
}


void DBManager::demoData()
{
    insertDemoSource();
}

void DBManager::insertDemoSource() {
    dbCheck();

   QStringList inserts = {
        //test

        // 1) источник (не падаем на повторах)
        R"SQL(
        INSERT INTO public.source (kind, domain, status, is_default)
        VALUES ('rss','https://www.vedomosti.ru/rss/news.xml','active', 'true')
        ON CONFLICT (kind, domain) DO NOTHING
        )SQL",

        // 2) TASS
        R"SQL(
        INSERT INTO public.source (kind, domain, status, is_default)
        VALUES ('rss','https://tass.ru/rss/v2.xml','active', 'true')
        ON CONFLICT (kind, domain) DO NOTHING
        )SQL",

        // 3) RBC
        R"SQL(
        INSERT INTO public.source (kind, domain, status, is_default)
        VALUES ('rss','https://rssexport.rbc.ru/rbcnews/news/30/full.rss','active', 'true')
        ON CONFLICT (kind, domain) DO NOTHING
        )SQL",

        // 4) The Guardian
        R"SQL(
        INSERT INTO public.source (kind, domain, status, is_default)
        VALUES ('rss','https://www.theguardian.com/world/rss','active', 'true')
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

QVariantMap DBManager::getSourceById(int id) {
    dbCheck();
    QVariantMap row;
    QSqlQuery q(db);
    q.prepare(R"SQL(
        SELECT id, domain, last_updated_at
        FROM public.source
        WHERE id = :id
        LIMIT 1
    )SQL");
    q.bindValue(":id", id);
    if (!q.exec()) {
        qWarning() << "getSourceById failed:" << q.lastError().text();
        return row;
    }
    if (q.next()) {
        row["id"]              = q.value(0).toInt();
        row["domain"]          = q.value(1).toString();
        row["last_updated_at"] = q.value(2).toDateTime();
    }
    return row;
}

bool DBManager::updateSourceStatus(int id, const QString& status) {
    dbCheck();
    QSqlQuery q(db);
    q.prepare(R"SQL(
        UPDATE public.source
        SET status = :st
        WHERE id = :id
    )SQL");
    q.bindValue(":st", status);
    q.bindValue(":id", id);
    if (!q.exec()) {
        qWarning() << "updateSourceStatus failed:" << q.lastError().text();
        return false;
    }
    return (q.numRowsAffected() >= 0);
}

QList<QVariantMap> DBManager::getClusterArticles(int clusterId, int limit) const {
    QList<QVariantMap> out;
    QSqlQuery q(db);
    q.prepare(R"SQL(
        SELECT title, summary
        FROM public.article
        WHERE cluster_id = :cid
        ORDER BY published_at DESC
        LIMIT :lim
    )SQL");
    q.bindValue(":cid", clusterId);
    q.bindValue(":lim", limit);
    if (!q.exec()) {
        qWarning() << "getClusterArticles failed:" << q.lastError().text();
        return out;
    }
    while (q.next()) {
        QVariantMap r;
        r["title"]   = q.value(0);
        r["summary"] = q.value(1);
        out.push_back(r);
    }
    return out;
}

// --- ensureTopic(title) ---
int DBManager::ensureTopic(const QString& title) {
    // 1) попытка найти id по title
    {
        QSqlQuery s(db);
        s.prepare(R"SQL(SELECT id FROM public.topic WHERE title = :t LIMIT 1)SQL");
        s.bindValue(":t", title);
        if (s.exec() && s.next()) return s.value(0).toInt();
    }
    // 2) вставка
    QSqlQuery q(db);
    q.prepare(R"SQL(
        INSERT INTO public.topic (title)
        VALUES (:t)
        ON CONFLICT (title) DO UPDATE SET title = EXCLUDED.title
        RETURNING id
    )SQL");
    q.bindValue(":t", title);
    if (!q.exec() || !q.next()) {
        qWarning() << "ensureTopic failed:" << q.lastError().text() << title;
        return 0;
    }
    return q.value(0).toInt();
}

// --- очистка primary для кластера ---
bool DBManager::clearClusterPrimary(int clusterId) {
    QSqlQuery q(db);
    q.prepare(R"SQL(
        UPDATE public.clustertopic
        SET "is_primary" = false
        WHERE cluster_id = :cid AND "is_primary" = true
    )SQL");
    q.bindValue(":cid", clusterId);
    if (!q.exec()) {
        qWarning() << "clearClusterPrimary failed:" << q.lastError().text();
        return false;
    }
    return true;
}

// --- UPSERT в cluster_topic ---
bool DBManager::upsertClusterTopic(int clusterId, int topicId, double score, bool primary) {
    QSqlQuery q(db);
    q.prepare(R"SQL(
        INSERT INTO public.clustertopic (cluster_id, topic_id, score, "is_primary")
        VALUES (:c, :t, :s, :p)
        ON CONFLICT (cluster_id, topic_id)
        DO UPDATE SET score = EXCLUDED.score, "is_primary" = EXCLUDED."is_primary"
    )SQL");
    q.bindValue(":c", clusterId);
    q.bindValue(":t", topicId);
    q.bindValue(":s", score);
    q.bindValue(":p", primary);
    if (!q.exec()) {
        qWarning() << "upsertClusterTopic failed:" << q.lastError().text();
        return false;
    }
    return true;
}