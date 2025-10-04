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

   

QVector<int> DBManager::insertArticles(const QList<QVariantMap>& rows) {
    dbCheck();
    QVector<int> ids; ids.reserve(rows.size());
    if (rows.isEmpty()) return ids;

    if (!db.transaction()) {
        qWarning() << "[insertArticles] tx begin failed:" << db.lastError().text();
        return {};
    }

    QSqlQuery q(db);
    // Важно: используем DEFAULT для хвостовых параметров функции (recency/веса/пороги)
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
            p_recency       => '3 days',
            p_min_score     => 0.2
        )
    )SQL");

    for (const auto& r : rows) {
        // Обязательные
        q.bindValue(":p_source_id",  r.value("source_id"));
        q.bindValue(":p_url",        r.value("url"));
        q.bindValue(":p_title",      r.value("title"));

        // Необязательные
        // image
        if (r.contains("image") && !r.value("image").isNull())
            q.bindValue(":p_image", r.value("image"));
        else
            q.bindValue(":p_image", QVariant(QVariant::String)); // NULL

        // summary
        if (r.contains("summary") && !r.value("summary").isNull())
            q.bindValue(":p_summary", r.value("summary"));
        else
            q.bindValue(":p_summary", QVariant(QVariant::String)); // NULL

        // published_at (лучше в UTC)
        {
            QDateTime dt = r.value("published_at").toDateTime();
            if (!dt.isValid()) {
                qWarning() << "[insertArticles] invalid published_at for url:" << r.value("url");
                db.rollback();
                return {};
            }
            // Если не указана таймзона — нормализуем в UTC
            if (dt.timeSpec() == Qt::LocalTime || dt.timeSpec() == Qt::TimeZone || dt.timeSpec() == Qt::OffsetFromUTC)
                dt = dt.toUTC();
            else if (dt.timeSpec() == Qt::UTC) {
                // ок
            } else {
                // Неизвестно — тоже в UTC
                dt = dt.toUTC();
            }
            q.bindValue(":p_published_at", dt);
        }

        // language
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
            // функция должна вернуть одну строку; если нет — это аномалия
            qWarning() << "[insertArticles] no row returned for url=" << r.value("url");
            q.finish();
            db.rollback();
            return {};
        }

        // Колонки: 0=cluster_id, 1=article_id, 2=score, 3=matched, 4=created_new
        const int articleId = q.value(1).toInt();
        ids.push_back(articleId);

        q.finish(); // обязательно чистим курсор перед следующим bind'ом
    }

    if (!db.commit()) {
        qWarning() << "[insertArticles] commit failed:" << db.lastError().text();
        return {};
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