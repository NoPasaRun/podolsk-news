#include "llm_topics.hpp"
#include <sys/stat.h>
#include <sstream>
#include <algorithm>
#include <cctype>
#include <cstdlib>
#include <cstring>
#include <stdexcept>
#include <unistd.h>

// llama.cpp C API (новый)
#include "llama.h"

bool LlmTopics::ensureInit() {
    if (impl_) return true;
    return init("");
}

struct LlmTopics::Impl {
    llama_model*   model = nullptr;
    llama_context* ctx   = nullptr;
    int n_ctx     = 2048;
    int n_threads = 4;

    ~Impl() {
        if (ctx)   { llama_free(ctx); ctx = nullptr; }
        if (model) { llama_model_free(model); model = nullptr; }
        llama_backend_free();
    }
};

static int detect_threads() {
#ifdef _SC_NPROCESSORS_ONLN
    long n = ::sysconf(_SC_NPROCESSORS_ONLN);
    return n > 0 ? int(n) : 4;
#else
    return 4;
#endif
}

LlmTopics::LlmTopics() {}
LlmTopics::~LlmTopics() { delete impl_; }


static bool file_exists(const std::string& p) {
    struct stat st{};
    return !p.empty() && ::stat(p.c_str(), &st) == 0 && S_ISREG(st.st_mode);
}

bool LlmTopics::init(const std::string& explicitPath) {
    std::lock_guard<std::mutex> lk(mtx_);
    if (impl_) return true;

    // 1) собираем кандидатов: explicit -> ENV -> compile-time
    std::vector<std::string> cand;
    if (!explicitPath.empty()) cand.push_back(explicitPath);

    if (const char* env = std::getenv("LLM_MODEL_PATH"); env && *env)
        cand.emplace_back(env);

#ifdef LLM_MODEL_PATH_STR
    if (std::string(LLM_MODEL_PATH_STR).size())
        cand.emplace_back(std::string(LLM_MODEL_PATH_STR));
#endif

    // 2) берём первый реально существующий файл
    std::string modelPath;
    for (const auto& c : cand) {
        if (file_exists(c)) { modelPath = c; break; }
    }
    // если ни один не существует — берём первый как есть (на авось)
    if (modelPath.empty() && !cand.empty()) modelPath = cand.front();
    if (modelPath.empty()) return false;

    // --- дальше как у тебя сейчас ---
    llama_backend_init();

    impl_ = new Impl();
    impl_->n_threads = detect_threads();

    llama_model_params mp = llama_model_default_params();
    impl_->model = llama_model_load_from_file(modelPath.c_str(), mp);
    if (!impl_->model) { delete impl_; impl_ = nullptr; return false; }

    llama_context_params cp = llama_context_default_params();
    cp.n_ctx = impl_->n_ctx;
    impl_->ctx = llama_init_from_model(impl_->model, cp);
    if (!impl_->ctx) { delete impl_; impl_ = nullptr; return false; }

    return true;
}

static std::string trim_ws(const std::string& s) {
    size_t a = 0, b = s.size();
    while (a < b && std::isspace(unsigned(s[a]))) ++a;
    while (b > a && std::isspace(unsigned(s[b-1]))) --b;
    return s.substr(a, b - a);
}

std::string LlmTopics::makePrompt(const std::string& text,
                                  const std::vector<std::string>& topics) {
    std::ostringstream allowed;
    allowed << "[";
    for (size_t i=0; i<topics.size(); ++i) { if (i) allowed << ", "; allowed << '"' << topics[i] << '"'; }
    allowed << "]";

    // Qwen ChatML + подсадка '{' чтобы модель дописывала JSON
    std::ostringstream oss;
    oss
      << "<|im_start|>system\n"
      << "You are a JSON-only classifier. Output strictly JSON, no prose.\n"
      << "Return 1 to 3 topics ONLY from the Allowed list, with scores 0..1.\n"
      << "Schema: {\"topics\":[{\"title\":\"<topic>\",\"score\":<float>}, ...]}\n"
      << "Use EXACT English labels from the Allowed list.\n"
      << "<|im_end|>\n"
      << "<|im_start|>user\n"
      << "Allowed: " << allowed.str() << "\n"
      << "Text:\n<<<\n" << text << "\n>>>\n"
      << "Answer with JSON only.\n"
      << "<|im_end|>\n"
      << "<|im_start|>assistant\n"
      << "{"; // ← крючок: модель продолжит внутри JSON
    return oss.str();
}


// Плоский запасной промпт (если ChatML вдруг молчит)
static std::string makePlainPrompt(const std::string& text,
                                   const std::vector<std::string>& topics) {
    std::ostringstream allowed;
    allowed << "[";
    for (size_t i=0; i<topics.size(); ++i) { if (i) allowed << ", "; allowed << '"' << topics[i] << '"'; }
    allowed << "]";
    std::ostringstream oss;
    oss
      << "You are a strict JSON-only news topic classifier.\n"
      << "Allowed: " << allowed.str() << "\n"
      << "Text:\n<<<\n" << text << "\n>>>\n"
      << "Respond ONLY JSON:\n"
      << R"({"topics":[{"title":"<topic>","score":0.0}, ...]})";
    return oss.str();
}

std::string LlmTopics::run(const std::string& prompt, int maxTokens) {
    if (!ensureInit()) return {};

    const llama_vocab* vocab = llama_model_get_vocab(impl_->model);

    auto tokenize = [&](const std::string& s, bool add_special){
        int32_t need = llama_tokenize(vocab, s.c_str(), (int32_t)s.size(),
                                      nullptr, 0, add_special, /*parse_special*/true);
        if (need <= 0) return std::vector<llama_token>{};
        std::vector<llama_token> v(need);
        llama_tokenize(vocab, s.c_str(), (int32_t)s.size(),
                       v.data(), (int32_t)v.size(), add_special, /*parse_special*/true);
        return v;
    };

    // 1) ChatML токенизация: ВАЖНО — add_special = false (у нас уже есть спец-токены в тексте)
    std::vector<llama_token> inp = tokenize(prompt, /*add_special*/false);
    if (inp.empty()) return {};

    // подготовим стоп-токен <|im_end|> (если он маппится в 1 токен)
    int32_t id_im_end = -1;
    {
        auto t = tokenize(std::string("<|im_end|>"), /*add_special*/false);
        if (t.size() == 1) id_im_end = t[0];
    }

    // 2) «скармливаем» промпт
    for (int i = 0; i < (int)inp.size(); ++i) {
        llama_batch batch = llama_batch_init(1, 0, 1);
        batch.n_tokens      = 1;
        batch.token[0]      = inp[i];
        batch.pos[0]        = i;
        batch.n_seq_id[0]   = 1;
        batch.seq_id[0][0]  = 0;
        batch.logits[0]     = (i == (int)inp.size() - 1);
        if (llama_decode(impl_->ctx, batch) != 0) { llama_batch_free(batch); return {}; }
        llama_batch_free(batch);
    }

    const int32_t eos_id   = llama_vocab_eos(vocab);
    const int32_t n_vocab  = llama_vocab_n_tokens(vocab);
    const int     n_predict = std::max(16, maxTokens);

    std::string out;
    out.reserve(512);

    for (int n = 0; n < n_predict; ++n) {
        const float* logits = llama_get_logits(impl_->ctx);
        if (!logits) break;

        // greedy
        int best_id = 0;
        float best_logit = logits[0];
        for (int t = 1; t < n_vocab; ++t) if (logits[t] > best_logit) { best_logit = logits[t]; best_id = t; }

        if (best_id == eos_id || (id_im_end >= 0 && best_id == id_im_end)) break;

        // добавляем текст (пропуская спец-токены по возможности)
        {
            char buf[8192];
            int n_ch = llama_token_to_piece(vocab, best_id, buf, (int)sizeof(buf), /*special*/0, /*lstrip*/true);
            if (n_ch > 0) out.append(buf, buf + n_ch);
        }

        llama_batch batch = llama_batch_init(1, 0, 1);
        batch.n_tokens      = 1;
        batch.token[0]      = best_id;
        batch.pos[0]        = (int)inp.size() + n;
        batch.n_seq_id[0]   = 1;
        batch.seq_id[0][0]  = 0;
        batch.logits[0]     = true;
        if (llama_decode(impl_->ctx, batch) != 0) { llama_batch_free(batch); break; }
        llama_batch_free(batch);

        if (!out.empty() && out.find('}') != std::string::npos) break;
    }

    // Если вдруг пусто — попробуем простым промптом как fallback
    if (out.empty()) {
        // Небольшая «подсказка» модели: выведи JSON прямо сейчас
        std::string plain = "Respond JSON now.\n";
        // подставим это как новый запрос: (в реальности проще — просто вернуть пусто)
        out = plain;
    }

    // отрезка пробелов
    while (!out.empty() && (unsigned char)out.back() <= ' ') out.pop_back();
    while (!out.empty() && (unsigned char)out.front() <= ' ') out.erase(out.begin());

    return out;
}

std::vector<TopicScore> LlmTopics::classify(
        const std::string& text,
        const std::vector<std::string>& topics,
        int topK,
        double minScore) {

    std::lock_guard<std::mutex> lk(mtx_);
    if (!ensureInit() || topics.empty() || text.empty()) return {};

	const std::string prompt = makePrompt(text, topics);
	std::string raw = run(prompt, 256);

	// fallback: если пусто — попробуем plain prompt (на случай, если ChatML не распознан)
	if (raw.empty()) {
		raw = run(makePlainPrompt(text, topics), 256);
	}

	fprintf(stderr, "[LlmTopics] RAW: %s\n", raw.c_str());
	fflush(stderr);

	if (raw.empty()) return {};

	// выкусываем JSON между { ... }
	auto l = raw.find('{');
	auto r = raw.rfind('}');
	if (l != std::string::npos && r != std::string::npos && r > l) {
		raw = raw.substr(l, r - l + 1);
	}

	// допускаем разный регистр ключей
	auto lower = [](std::string s){ for(char& c: s) c = (char)std::tolower((unsigned char)c); return s; };
	std::string raw_lc = lower(raw);

	// основной разбор: ищем пары "title": "...", "score": num
	std::vector<TopicScore> out;
	size_t pos = 0;
	while (true) {
		size_t t1 = raw_lc.find("\"title\"", pos);
		if (t1 == std::string::npos) break;
		size_t q1 = raw.find('"', raw.find(':', t1) + 1);
		if (q1 == std::string::npos) break;
		size_t q2 = raw.find('"', q1 + 1);
		if (q2 == std::string::npos) break;
		std::string title = raw.substr(q1 + 1, q2 - q1 - 1);

		size_t s1 = raw_lc.find("\"score\"", q2);
		if (s1 == std::string::npos) { pos = q2 + 1; continue; }
		size_t col = raw.find(':', s1);
		if (col == std::string::npos) { pos = q2 + 1; continue; }
		size_t endnum = raw.find_first_of(",}]", col + 1);
		std::string sv = raw.substr(col + 1, endnum == std::string::npos ? std::string::npos : endnum - (col + 1));
		double sc = 0.0; try { sc = std::stod(sv); } catch (...) { sc = 0.0; }
		if (sc > 0.0) out.push_back({title, std::min(1.0, std::max(0.0, sc))});

		pos = (endnum == std::string::npos ? raw.size() : endnum);
		if ((int)out.size() >= topK) break;
	}

    // фильтр по whitelisт'у
    std::vector<std::string> allowed = topics;
    std::sort(allowed.begin(), allowed.end());
    std::vector<TopicScore> filtered;
    filtered.reserve(out.size());
    for (auto &ts : out) if (std::binary_search(allowed.begin(), allowed.end(), ts.title)) filtered.push_back(ts);

    std::sort(filtered.begin(), filtered.end(),
              [](const TopicScore& a, const TopicScore& b){ return a.score > b.score; });

    if ((int)filtered.size() > topK) filtered.resize(topK);
    return filtered;
}
