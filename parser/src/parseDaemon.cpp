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

QString ParseDaemon::languageCheck(QString text)    //ПРОХОДИТ ВСЮ СТРОКУ, В НЕКТОРЫХ СЛУЧАЯХ МОЖНО ОБОЙТИСЬ ПЕРВЫМ СЛОВОМ ИЛИ ДАЖЕ ПЕРВОЙ БУКВОЙ
{

    QList<QChar> russianChars = {QChar('а'), QChar('б'), QChar('в'), QChar('г'), QChar('д'), QChar('е'), QChar('ё'), QChar('ж'), QChar('з'), QChar('и'), QChar('й'), QChar('к'), QChar('л'), QChar('м'), QChar('н'), QChar('о'), QChar('п'), QChar('р'), QChar('с'), QChar('т'), QChar('у'), QChar('ф'), QChar('х'), QChar('ц'), QChar('ч'), QChar('ш'), QChar('щ'), QChar('ъ'), QChar('ы'), QChar('ь'), QChar('э'), QChar('ю'), QChar('я')};
    QList<QChar> germanChars  = {QChar('ä'), QChar('ö'), QChar('ü'), QChar('ß')};
    QList<QChar> spanishChars = {QChar('ñ'), QChar('á'), QChar('é'), QChar('í'), QChar('ó'), QChar('ú')};
    QList<QChar> englishChars = {QChar('a'), QChar('b'), QChar('c'), QChar('d'), QChar('e'), QChar('f'), QChar('g'), QChar('h'), QChar('i'), QChar('j'), QChar('k'), QChar('l'), QChar('m'), QChar('n'), QChar('o'), QChar('p'), QChar('q'), QChar('r'), QChar('s'), QChar('t'), QChar('u'), QChar('v'), QChar('w'), QChar('x'), QChar('y'), QChar('z')};
    for (const auto& ch : text) {
        if (russianChars.contains(ch)) {
            return "ru";
        } else if (germanChars.contains(ch)) {
            return "de"; 
        } else if (spanishChars.contains(ch)) {
            return "es"; 
        }else if (englishChars.contains(ch)) {
            return "en"; 
        }
    }

    return "ru"; // Если язык не определён

}



QDateTime parsePublishedAtUtc(const feedpp::item& it) {
    // 1) Текстовая дата (в RSS есть таймзона) — приоритетно
    if (!it.pubDate.empty()) {
        const QString s = QString::fromStdString(it.pubDate);
        QDateTime dt = QDateTime::fromString(s, Qt::RFC2822Date);
        if (!dt.isValid()) dt = QDateTime::fromString(s, Qt::ISODate);
        if (dt.isValid()) {
            const QDateTime out = dt.toUTC();
            if (out.date().year() >= 1990 && out.date().year() <= 2100) // sanity для новостей
                return out;
        }
    }

    // 2) Числовой timestamp — определяем единицы
    if (it.pubDate_ts > 0) {
        qint64 v = static_cast<qint64>(it.pubDate_ts);
        QDateTime dt;

        if (v >= 100000000000000LL) {        // >= 1e14 → микросекунды
            dt = QDateTime::fromMSecsSinceEpoch(v / 1000, Qt::UTC);
        } else if (v >= 1000000000000LL) {   // >= 1e12 → миллисекунды
            dt = QDateTime::fromMSecsSinceEpoch(v, Qt::UTC);
        } else {                              // секунды
            dt = QDateTime::fromSecsSinceEpoch(v, Qt::UTC);
        }

        if (dt.isValid() && dt.date().year() >= 1990 && dt.date().year() <= 2100)
            return dt;
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

  
        const int sourceId = src.value("id").toInt();
        const QString feedUrl = src.value("domain").toString();
        QDateTime lastUpdate = src.value("last_updated_at").toDateTime();


        try
        {
            // парсим фид
            feedpp::feed f = p.parse_url(feedUrl.toStdString());

            const QString feedLang = {languageCheck(QString::fromStdString(f.title))};

            QList<QVariantMap> batch;
            batch.reserve(BATCH_SIZE);

            // 2.2 конвертим items -> строки для БД
            for (const auto &it : f.items)
            {
                QDateTime feedPublishedAt = parsePublishedAtUtc(it);

                // фильтр: только новее последнего апдейта источника
                if (lastUpdate.isValid() && !(feedPublishedAt > lastUpdate)) {
                    static int oldNews = 0;
                    qDebug() << "Новость древняя, пропускаем " << oldNews++;
                    continue;
                }

                QVariantMap row{
                    {"url",                 QString::fromStdString(it.link)},
                    {"url_canon",           QString()},                     // placeholder
                    {"title",               QString::fromStdString(it.title)},
                    {"summary",             QString::fromStdString(it.description)},
                    {"content_html",        QString()},                     // placeholder
                    {"published_at",        feedPublishedAt},
                    {"language",            feedLang},
                    {"content_fingerprint", QString()},                      // placeholder
                    {"source_id",           sourceId}
                };


                batch.push_back(std::move(row));

                if (batch.size() == BATCH_SIZE)
                {
                    DBMg.insertArticles(batch);
                    batch.clear();
                }
            }

            // Хвост
            if (!batch.isEmpty())
            {
                DBMg.insertArticles(batch);
                batch.clear();
            }

            qDebug() << "Source" << sourceId << "parsed:" << f.items.size() << "items";
            qDebug() << ticks++ << " :tick";
        }
        catch (const ::exception &ex)
        {
            qWarning() << "Feed parse error for source" << sourceId << ":" << ex.what();
            continue;
        }
    }
}
