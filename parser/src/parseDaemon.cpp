#include "parseDaemon.hpp"
#include <QDebug>
#include <QtSql/QSqlError>

constexpr int BATCH_SIZE = 50;  //По сколько закидывать новостей в бдшку

ParseDaemon::ParseDaemon(QObject* parent) : QObject(parent) {
    connect(&timer, &QTimer::timeout, this, &ParseDaemon::tick);
    
}

ParseDaemon::~ParseDaemon() {
    
    feedpp::parser::global_cleanup();
    delete llmTopics_; llmTopics_ = nullptr;
}


void ParseDaemon::start() {
    feedpp::parser::global_init();
    DBMg.open();

    // 1) грузим темы из БД и строим кэш
    topicLabels_.clear();
    topicKeyToId_.clear();
    for (const auto &r : DBMg.listTopics()) {
        topicLabels_ << r.title;
        topicKeyToId_.insert(normKey(r.title), r.id);
    }
    if (topicLabels_.isEmpty())
        qWarning() << "[ParseDaemon] topic table is empty – classification will be skipped";

    // 2) LLM
    llmTopics_ = new LlmTopics(LlmTopics::Options{});
    if (!llmTopics_->init())
        qWarning() << "LLM (topics) init failed";

    // дальше как было...
    timer.start(DBMg.config.lazy_time * 1000);
    DBMg.demoData();
    tick();
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
                DBMg.insertArticlesDetailed(batch);
                batch.clear();
            }
        }
        if (!batch.isEmpty()) {
            auto results = DBMg.insertArticlesDetailed(batch);     // ← было insertArticles
            classifyNewClustersSingle(results, batch, /*lang*/ feedLang);
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

void ParseDaemon::classifyNewClustersSingle(const QVector<ArticleInsertResult>& results,
                                            const QList<QVariantMap>& rows,
                                            const QString& lang) {
    if (!llmTopics_ || topicLabels_.isEmpty()) return;

    const int n = std::min(results.size(), rows.size());

    for (int i = 0; i < n; ++i) {
        const auto& r = results[i];
        if (!r.createdNew) continue; // только для новых кластеров

        const auto& row = rows[i];
        QString text = (row.value("title").toString() + ". " +
                        row.value("summary").toString()).trimmed();
        if (text.isEmpty()) text = row.value("title").toString();
        if (text.isEmpty()) continue;

        // 1) скорим по БД-шному списку title
        auto scored = llmTopics_->scoreLabels(text, topicLabels_, lang);
        if (scored.isEmpty()) continue;

        // 2) берём ТОП-3 и сопоставляем с id
        QVector<TopicScore> toSave;
        const int cap = std::min<int>(3, scored.size());
        toSave.reserve(cap);

        int kept = 0;
        for (int j = 0; j < scored.size() && kept < cap; ++j) {
            const auto &sl = scored[j];
            const int tid = topicKeyToId_.value(normKey(sl.label), -1);
            if (tid <= 0) continue;   // неизвестный label — пропускаем
            toSave.push_back(TopicScore{ tid, sl.score, kept == 0 });
            ++kept;
        }

        if (!toSave.isEmpty())
            DBMg.upsertClusterTopics(r.clusterId, toSave);
    }
}


QString ParseDaemon::normKey(const QString& s) {
    QString t = s.trimmed().toLower();
    t.remove(' '); t.remove('_'); t.remove('-');
    return t;
}