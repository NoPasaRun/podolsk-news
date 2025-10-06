#include "llm_topics.hpp"
#include <QJsonDocument>
#include <QJsonObject>
#include <QJsonValue>
#include <QRegularExpression>
#include <algorithm>
#include <cmath>
#include <unistd.h>
#include <algorithm>
#include <vector>  // на случай, если кто-то подключит llama.h здесь

static const char* kAllTopicsCSV =
"Politics,Business,Tech,Science,Health,Sports,Entertainment,Culture,Education,Travel,Cars,Finance,Crime,War";

LlmTopics::~LlmTopics(){ destroy(); }

int LlmTopics::detectThreads() {
#ifdef _SC_NPROCESSORS_ONLN
    long n = ::sysconf(_SC_NPROCESSORS_ONLN);
    return n>0 ? int(n) : 4;
#else
    return 4;
#endif
}

std::string LlmTopics::toStd(const QString& s) {
    const QByteArray b = s.toUtf8();
    return std::string(b.constData(), size_t(b.size()));
}

bool LlmTopics::init(){
    if (model_) return true;
    if (opt_.n_threads<=0) opt_.n_threads = detectThreads();

    llama_backend_init();

    llama_model_params mp = llama_model_default_params();
    model_ = llama_model_load_from_file(toStd(opt_.modelPath).c_str(), mp);
    if (!model_) return false;

    llama_context_params cp = llama_context_default_params();
    cp.n_ctx     = opt_.n_ctx;
    cp.n_threads = opt_.n_threads;
    ctx_ = llama_init_from_model(model_, cp);
    if (!ctx_) return false;

    vocab_ = llama_model_get_vocab(model_);
    return true;
}

void LlmTopics::destroy(){
    if (ctx_)   { llama_free(ctx_); ctx_ = nullptr; }
    if (model_) { llama_model_free(model_); model_ = nullptr; } // <-- не llama_free_model
    vocab_ = nullptr;
}

QString LlmTopics::generate(const QString& userPrompt){
    // 1) Qwen chat template
    QString chat =
        "<|im_start|>system\n"
        "You are a strict JSON generator. Reply ONLY with one JSON object.\n"
        "<|im_end|>\n"
        "<|im_start|>user\n" + userPrompt + "\n<|im_end|>\n"
        "<|im_start|>assistant\n";

    const std::string sp = toStd(chat);

    // 2) tokenize (для Qwen add_bos = false)
    int32_t need = llama_tokenize(vocab_, sp.c_str(), (int32_t)sp.size(),
                                  nullptr, 0, /*add_bos*/false, /*special*/true);
    if (need <= 0) return {};

    std::vector<llama_token> tok(need);
    llama_tokenize(vocab_, sp.c_str(), (int32_t)sp.size(),
                   tok.data(), (int32_t)tok.size(), /*add_bos*/false, /*special*/true);

    llama_batch b = llama_batch_init((int32_t)tok.size(), 0, 1);
    for (int i = 0; i < (int)tok.size(); ++i) {
        b.token[i]     = tok[i];
        b.pos[i]       = i;
        b.n_seq_id[i]  = 1;
        b.seq_id[i][0] = 0;
        b.logits[i]    = (i == (int)tok.size() - 1);
    }
    b.n_tokens = (int32_t)tok.size();

    if (llama_decode(ctx_, b) != 0) { llama_batch_free(b); return {}; }
    llama_batch_free(b);
    int n_past = (int)tok.size();

    QString out;
    const llama_token eos = llama_vocab_eos(vocab_);
    const int min_tokens  = 8;             // не даём завершиться слишком рано
    for (int t = 0; t < opt_.max_tokens; ++t) {
        const float* logits = llama_get_logits_ith(ctx_, -1);
        const int n_vocab = llama_vocab_n_tokens(vocab_);

        // выбираем лучшую НЕ-EOS, пока не набрали min_tokens
        int best = -1; float bestv = -1e30f;
        for (int i = 0; i < n_vocab; ++i) {
            if (t < min_tokens && i == eos) continue;
            if (logits[i] > bestv) { bestv = logits[i]; best = i; }
        }
        if (best == -1 || best == eos) break;

        const char* piece = llama_vocab_get_text(vocab_, best);
        if (!piece) break;
        out += QString::fromUtf8(piece);
        if (out.contains('}')) break;

        llama_batch one = llama_batch_init(1, 0, 1);
        one.token[0]     = best;
        one.pos[0]       = n_past;
        one.n_seq_id[0]  = 1;
        one.seq_id[0][0] = 0;
        one.logits[0]    = true;
        one.n_tokens     = 1;

        n_past += 1;
        if (llama_decode(ctx_, one) != 0) { llama_batch_free(one); break; }
        llama_batch_free(one);
    }

    // на всякий случай
    if (out.trimmed().isEmpty()) {
        qWarning() << "[LLM] empty generation after decode";
    }
    return out;
}

QVector<ScoredLabel> LlmTopics::scoreLabels(const QString& text,
                                            const QStringList& labels,
                                            const QString& /*lang*/) {
    QVector<ScoredLabel> out;
    if (!ctx_ || labels.isEmpty()) return out;

    // 1) строим JSON-массив меток ровно как в БД
    const QString list = "[\"" + labels.join("\",\"") + "\"]";

    // 2) строгий промпт на JSON
    QString prompt =
        "Ты — классификатор тем. Дано: список тем (JSON-массив строк) и текст новости.\n"
        "Верни ТОЛЬКО один JSON-объект без пояснений и префиксов, строго вида:\n"
        "{\"<label>\": <score>, ...}\n"
        "Требования: ключи ДОЛЖНЫ в точности совпадать со списком ниже; значения — числа 0..1; "
        "сумма ≈ 1; не добавляй новых ключей и не пропускай существующие.\n"
        "labels = " + list + "\n"
        "text:\n" + text.left(2000);

    const QString raw = generate(prompt);
    // ЛОГ (см. раздел «Логи» ниже)
    qDebug() << "[LLM raw]" << raw.left(300);

    // 3) парсим JSON-объект
    QMap<QString,double> m;
    for (const auto &l : labels) m[l] = 0.0;

    QJsonParseError perr{};
    const auto doc = QJsonDocument::fromJson(raw.toUtf8(), &perr);

    bool ok = false;
    if (perr.error == QJsonParseError::NoError && doc.isObject()) {
        const auto obj = doc.object();
        // принимаем только ключи из labels
        double sum = 0.0;
        for (const auto &l : labels) {
            if (obj.contains(l) && obj[l].isDouble()) {
                double v = std::clamp(obj[l].toDouble(), 0.0, 1.0);
                m[l] = v; sum += v;
            }
        }
        if (sum > 0) {
            for (auto it = m.begin(); it != m.end(); ++it) it.value() /= sum;
            ok = true;
        }
    }

    // 4) фолбэк: если пришло одно слово/лейбл — считаем его 1.0
    if (!ok) {
        const QString trimmed = raw.trimmed().remove('"');
        QString picked;
        // точное совпадение
        for (const auto &l : labels) {
            if (QString::compare(l, trimmed, Qt::CaseInsensitive) == 0) { picked = l; break; }
        }
        // частичное (на случай «Tech.»/«Политика.»)
        if (picked.isEmpty()) {
            for (const auto &l : labels) {
                if (trimmed.contains(l, Qt::CaseInsensitive)) { picked = l; break; }
            }
        }
        if (!picked.isEmpty()) {
            for (auto it = m.begin(); it != m.end(); ++it) it.value() = 0.0;
            m[picked] = 1.0;
            ok = true;
        }
    }

    // 5) если всё ещё не ок — мягкий равномерный (но это редкий случай)
    if (!ok) {
        const double x = 1.0 / double(m.size());
        for (auto it = m.begin(); it != m.end(); ++it) it.value() = x;
    }

    // 6) вектор + сортировка
    out.reserve(m.size());
    for (auto it = m.begin(); it != m.end(); ++it) out.push_back({ it.key(), it.value() });
    std::sort(out.begin(), out.end(), [](auto &a, auto &b){ return a.score > b.score; });

    // ЛОГ итогов
    const int top = std::min(5, int(out.size()));   // 👈 привели size к int
    QStringList dbg;
    dbg.reserve(top);
    for (int i = 0; i < top; ++i) {
        dbg << (out[i].label + ":" + QString::number(out[i].score,'f',3));
    }

    return out;
}
