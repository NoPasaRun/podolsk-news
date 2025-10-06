#include "parseDaemon.hpp"
#include <QDebug>
#include <QtSql/QSqlError>

constexpr int BATCH_SIZE = 50;  //По сколько закидывать новостей в бдшку

ParseDaemon::ParseDaemon(QObject* parent) : QObject(parent) {
    connect(&timer, &QTimer::timeout, this, &ParseDaemon::tick);
    
}

ParseDaemon::~ParseDaemon() {
    
    feedpp::parser::global_cleanup();
}


void ParseDaemon::start() {
    feedpp::parser::global_init();
    DBMg.open();
    timer.start(DBMg.config.lazy_time * 1000); //в лази тайм надо указать время в секундах
    DBMg.demoData();
    tick(); // сразу первый запуск
}


QString ParseDaemon::languageCheck(QStringView text)
{
    for (QChar ch : text) {
        if (!ch.isLetter())
            continue;

        const QChar c = ch.toLower();       // один раз к нижнему регистру
        const ushort u = c.unicode();

        // --- Русский (кириллица "а".."я" + "ё") ---
        // 'а'..'я' = 0x0430..0x044F, 'ё' = 0x0451
        if ((u >= 0x0430 && u <= 0x044F) || u == 0x0451)
            return QStringLiteral("russian");

        // --- Немецкий маркёры: ä ö ü ß ---
        if (u == 0x00E4 || u == 0x00F6 || u == 0x00FC || u == 0x00DF)
            return QStringLiteral("german");

        // --- Испанский маркёры: ñ á é í ó ú ---
        if (u == 0x00F1 || u == 0x00E1 || u == 0x00E9 ||
            u == 0x00ED || u == 0x00F3 || u == 0x00FA)
            return QStringLiteral("spanish");

        // --- Базовая латиница (английский) ---
        if (u >= 'a' && u <= 'z')
            return QStringLiteral("english");

        // Если попали сюда — буква не из наших маркёров, идём дальше.
    }

    // Фолбэк как у тебя
    return QStringLiteral("russian");
}


QDateTime parsePublishedAtUtc(const feedpp::item& it) {
    auto okRange = [](const QDateTime& d){
        return d.isValid() && d.date().year() >= 1990 && d.date().year() <= 2100;
    };

    // 1) Текстовая дата
    if (!it.pubDate.empty()) {
    	qWarning() << "[ReactService] shit " << it.pubDate;
        const QString s = QString::fromStdString(it.pubDate).trimmed();
        QDateTime dt = QDateTime::fromString(s, Qt::RFC2822Date);
        if (!dt.isValid()) dt = QDateTime::fromString(s, Qt::ISODate);
        if (!dt.isValid()) dt = QDateTime::fromString(s, Qt::ISODateWithMs); // ← добавили
        if (okRange(dt)) return dt.toUTC();
    }

    // 2) Числовой timestamp (s/ms/µs/ns)
    if (it.pubDate_ts > 0) {
        const qint64 v = static_cast<qint64>(it.pubDate_ts);
        QDateTime dt;
        if      (v >= 1'000'000'000'000'000'000LL) dt = QDateTime::fromMSecsSinceEpoch(v / 1'000'000, Qt::UTC); // ns→ms
        else if (v >=     100'000'000'000'000LL)   dt = QDateTime::fromMSecsSinceEpoch(v / 1'000,     Qt::UTC); // µs→ms
        else if (v >=       1'000'000'000'000LL)   dt = QDateTime::fromMSecsSinceEpoch(v,             Qt::UTC); // ms
        else                                       dt = QDateTime::fromSecsSinceEpoch(v,              Qt::UTC); // s
        if (okRange(dt)) return dt;
    }

    // 3) Фолбэк
    return QDateTime::currentDateTimeUtc();
}

static int ticks = 0;

void ParseDaemon::tick() {
    qDebug() << "tick";

    for (;;) // КОРОЧЕ ЦИКЛА ТУТ НЕ ПРОИСХОДИТ, СНИЗУ БРИК А СУРСЫ МЫ ПОЛУЧАЕМ ВСЕ
    {
        
        const QList<QVariantMap> sources = DBMg.listRssSourcesRange(0, 100000);
        DBMg.bumpSourcesLastUpdatedRange(0, 100000, QDateTime::currentDateTimeUtc());
        if (sources.isEmpty()) {
            qDebug() << "No RSS sources";
            return;
        }

        parceSources(sources);

        break;
    }
}

void ParseDaemon::parceSources(const QList<QVariantMap> &sources)
{
    feedpp::parser p(/*timeout*/ 7, /*UA*/ "PodolskNews/1.0");

    for (const auto &src : sources)
    {
        QString err;
        if (!parseOneSourceWithParser(p, src, &err)) {
            const int sid = src.value("id").toInt();
            qWarning() << "Feed parse error for source" << sid << ":" << err;
        }
    }
}

bool ParseDaemon::parseOneSourceWithParser(feedpp::parser& p,
                                           const QVariantMap& src,
                                           QString* err)
{
    const int      sourceId   = src.value("id").toInt();
    const QString  feedUrl    = src.value("domain").toString();
    const QDateTime lastUpdate = src.value("last_updated_at").toDateTime();

    try {
        feedpp::feed f = p.parse_url(feedUrl.toStdString());
        const QString feedLang = languageCheck(QString::fromStdString(f.title));

        QList<QVariantMap> batch;
        batch.reserve(50);

        for (const auto &it : f.items) {
            const QDateTime feedPublishedAt = parsePublishedAtUtc(it);
            if (lastUpdate.isValid() && !(feedPublishedAt > lastUpdate)) {
                continue;
            }

            QVariantMap row{
                {"url",                 QString::fromStdString(it.link)},
                {"url_image",           QString::fromStdString(it.enclosure_url)},
                {"url_type",            QString::fromStdString(it.enclosure_type)},
                {"title",               QString::fromStdString(it.title)},
                {"summary",             QString::fromStdString(it.description)},
                {"guid",                QString::fromStdString(it.guid)},
                {"published_at",        feedPublishedAt},
                {"language",            feedLang},
                {"content_fingerprint", QString()},
                {"source_id",           sourceId}
            };

            batch.push_back(std::move(row));
            if (batch.size() >= 50) {
                DBMg.insertArticles(batch);
                batch.clear();
            }
        }
        if (!batch.isEmpty()) {
            DBMg.insertArticles(batch);
            batch.clear();
        }

        qDebug() << "Source" << sourceId << "parsed:" << f.items.size() << "items";
        return true;
    } catch (const std::exception& e) {
        if (err) *err = QString::fromUtf8(e.what());
        return false;
    }
}

bool ParseDaemon::parseOneSourceById(int sourceId, QString* errorOut)
{
    const QVariantMap src = DBMg.getSourceById(sourceId);
    if (src.isEmpty()) {
        if (errorOut) *errorOut = "source_not_found";
        return false;
    }
    feedpp::parser p(/*timeout*/ 7, /*UA*/ "PodolskNews/1.0");
    return parseOneSourceWithParser(p, src, errorOut);
}

bool ParseDaemon::setSourceStatus(int sourceId, const QString& status)
{
    return DBMg.updateSourceStatus(sourceId, status);
}
