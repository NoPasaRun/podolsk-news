#include "topic_assigner.hpp"
#include "llm_topics.hpp"
#include "databaseManager.hpp"
#include <QVariantMap>
#include <QDebug>
#include <unordered_map>

static QString canonicalizeTopic(const QString& in) {
    const QString s = in.trimmed().toLower();
    static const std::unordered_map<QString, QString> map = {
        // EN -> EN
        { "politics","Politics" }, { "business","Business" }, { "tech","Tech" },
        { "technology","Tech" }, { "science","Science" }, { "health","Health" },
        { "sports","Sports" }, { "sport","Sports" }, { "entertainment","Entertainment" },
        { "culture","Culture" }, { "education","Education" }, { "travel","Travel" },
        { "cars","Cars" }, { "auto","Cars" }, { "finance","Finance" },
        { "crime","Crime" }, { "war","War" },

        // RU -> EN
        { "политика","Politics" }, { "бизнес","Business" }, { "экономика","Business" },
        { "технологии","Tech" }, { "техника","Tech" }, { "наука","Science" },
        { "здоровье","Health" }, { "спорт","Sports" }, { "развлечения","Entertainment" },
        { "культура","Culture" }, { "образование","Education" }, { "путешествия","Travel" },
        { "туризм","Travel" }, { "авто","Cars" }, { "машины","Cars" },
        { "финансы","Finance" }, { "криминал","Crime" }, { "преступления","Crime" },
        { "война","War" }, { "конфликт","War" }, { "фронт","War" },

        // DE -> EN
        { "politik","Politics" }, { "wirtschaft","Business" }, { "technik","Tech" },
        { "wissenschaft","Science" }, { "gesundheit","Health" }, { "sport","Sports" },
        { "unterhaltung","Entertainment" }, { "kultur","Culture" }, { "bildung","Education" },
        { "reisen","Travel" }, { "autos","Cars" }, { "finanzen","Finance" },
        { "kriminalität","Crime" }, { "krieg","War" },

        // ES -> EN
        { "política","Politics" }, { "negocios","Business" }, { "empresa","Business" },
        { "tecnología","Tech" }, { "ciencia","Science" }, { "salud","Health" },
        { "deportes","Sports" }, { "entretenimiento","Entertainment" }, { "cultura","Culture" },
        { "educación","Education" }, { "viajes","Travel" }, { "autos","Cars" }, { "coches","Cars" },
        { "finanzas","Finance" }, { "crimen","Crime" }, { "delito","Crime" }, { "guerra","War" },
    };
    auto it = map.find(s);
    if (it != map.end()) return it->second;
    return QString();
}

static QString toLowerSpaces(const QString& s) {
    QString t = s.toLower();
    t.replace(QRegularExpression("[^\\p{L}\\p{N}]+"), " ");
    return t.simplified();
}

// ключевые слова по темам (RU/EN/DE/ES)
static const QHash<QString, QStringList>& topicKeywords() {
    static QHash<QString, QStringList> m = {
        { "Politics",      { "политик","дума","парламент","выбор", "санкц", "президент",
                             "ministry","parliament","election","sanction","president",
                             "bundestag","regierung","wahl","sanction" } },
        { "Business",      { "бизнес","компания","рынок","банк","сделка","инвести",
                             "company","market","bank","deal","merger","ipo",
                             "unternehmen","markt","firma","fusion" } },
        { "Tech",          { "технол","ит","софт","стартап","искусств", "алгоритм","крипто",
                             "tech","software","ai","startup","algorithm","crypto",
                             "technik","ki","software" } },
        { "Science",       { "ученые","исслед","наука","эксперимент","космос",
                             "scientist","research","study","experiment","space",
                             "wissenschaft","forschung" } },
        { "Health",        { "здоров","врач","медици","вакцин","болезн",
                             "health","doctor","medical","vaccine","disease",
                             "gesundheit","arzt","medizin" } },
        { "Sports",        { "спорт","матч","турнир","лига","гол","футбол","хоккей",
                             "sport","match","tournament","league","goal","football","soccer",
                             "spiel","liga","tor" } },
        { "Entertainment", { "кино","фильм","сериал","шоу","певец","актёр","звезда",
                             "movie","film","series","show","singer","actor","celebrity",
                             "unterhaltung","film","serie" } },
        { "Culture",       { "культура","театр","музей","книг","литерат","выставк",
                             "culture","theatre","museum","book","literature","exhibit",
                             "kultur","theater","museum" } },
        { "Education",     { "образован","университет","школ","студент","экзамен",
                             "education","university","school","student","exam",
                             "bildung","schule","universität" } },
        { "Travel",        { "туризм","путешеств","виза","аэропорт","рейс","отель",
                             "travel","tourism","visa","airport","flight","hotel",
                             "reise","flug","hotel" } },
        { "Cars",          { "авто","машин","электромоб","tesla","двигател","дтп",
                             "car","auto","vehicle","ev","engine","accident",
                             "auto","fahrzeug","ev" } },
        { "Finance",       { "финанс","акция","облигац","ставка","курс","рубл","доллар",
                             "finance","stock","bond","rate","usd","eur",
                             "finanz","aktie","anleihe","zins" } },
        { "Crime",         { "криминал","убий","краж","арест","полици","суд",
                             "crime","murder","theft","arrest","police","court",
                             "kriminalität","mord","diebstahl","verhaftung" } },
        { "War",           { "война","фронт","армия","удар","ракет","боестолк","конфликт",
                             "war","front","army","strike","missile","conflict",
                             "krieg","armee","konflikt" } },
    };
    return m;
}

// простой бэкап-оценщик по ключевым словам
static std::vector<std::pair<QString,double>> heuristicTopicsFromText(const QString& text) {
    const QString t = toLowerSpaces(text);
    QHash<QString,int> hits;
    int maxHit = 0;

    for (auto it = topicKeywords().cbegin(); it != topicKeywords().cend(); ++it) {
        int cnt = 0;
        for (const QString& kw : it.value()) {
            if (t.contains(kw)) ++cnt;
        }
        if (cnt > 0) {
            hits[it.key()] = cnt;
            if (cnt > maxHit) maxHit = cnt;
        }
    }

    std::vector<std::pair<QString,double>> out;
    if (maxHit == 0) return out;

    for (auto it = hits.cbegin(); it != hits.cend(); ++it) {
        double score = double(it.value()) / double(maxHit); // 0..1
        out.emplace_back(it.key(), score);
    }
    std::sort(out.begin(), out.end(), [](auto& a, auto& b){ return a.second > b.second; });
    if (out.size() > 3) out.resize(3);
    return out;
}

TopicAssigner::TopicAssigner(DBManager& db) : db_(db) {
    llm_ = new LlmTopics();
    if (!llm_->init("")) {
        qWarning() << "[TopicAssigner] LLM init failed (check LLM_MODEL_PATH)";
    }
}

TopicAssigner::~TopicAssigner() { delete llm_; }

std::vector<std::string> TopicAssigner::topicList() const {
    // Можно вынести в конфиг
    static const char* k[] = {
        "Politics","Business","Tech","Science","Health","Sports","Entertainment",
        "Culture","Education","Travel","Cars","Finance","Crime","War"
    };
    std::vector<std::string> v;
    v.reserve(std::size(k));
    for (auto &t : k) v.emplace_back(t);
    return v;
}

std::string TopicAssigner::buildClusterText(int clusterId, int limitArticles) {
    const QList<QVariantMap> arts = db_.getClusterArticles(clusterId, limitArticles);

    std::string s;
    s.reserve(2048);
    s += "Cluster #" + std::to_string(clusterId) + " sample:\n";
    int i = 1;
    for (const auto& a : arts) {
        const QString title   = a.value("title").toString();
        const QString summary = a.value("summary").toString();
        s += std::to_string(i++) + ") " + title.toStdString() + "\n";
        if (!summary.isEmpty())
            s += "   " + summary.left(600).toStdString() + "\n";
    }
    return s;
}

void TopicAssigner::assignForClusters(const QSet<int>& clusterIds) {
    if (!llm_) return;
    const auto labels = topicList();

    for (int cid : clusterIds) {
        const std::string ctx = buildClusterText(cid, 6);
        if (ctx.empty()) continue;

        auto scores = llm_->classify(ctx, labels, /*topK*/3, /*minScore*/0.15);

        // если пусто — скипаем, без мусора
		if (scores.empty()) {
			// соберём компактный текст из статей кластера
			const QList<QVariantMap> arts = db_.getClusterArticles(cid, 6);
			QString t;
			for (const auto& a : arts) {
				if (!a.value("title").toString().isEmpty())
					t += a.value("title").toString() + " ";
				if (!a.value("summary").toString().isEmpty())
					t += a.value("summary").toString() + " ";
			}
			const auto heur = heuristicTopicsFromText(t);
			for (auto &h : heur) {
				const QString canon = canonicalizeTopic(h.first);
				if (canon.isEmpty()) continue;
				scores.push_back({ canon.toStdString(), std::min(1.0, std::max(0.0, h.second)) });
			}
		}

        // апдейт в БД
        // 1) очищаем primary у кластера
		db_.clearClusterPrimary(cid);
		int rank = 0;
		for (auto &ts : scores) {
			const QString canon = canonicalizeTopic(QString::fromStdString(ts.title));
			if (canon.isEmpty()) continue;
			int topicId = db_.ensureTopic(canon);
			if (topicId <= 0) continue;
			const bool primary = (rank == 0);
			db_.upsertClusterTopic(cid, topicId, ts.score, primary);
			++rank;
		}
    }
}
