#pragma once
#include <QString>
#include <QStringList>
#include <QVector>
#include <llama.h>

struct ScoredLabel { QString label; double score; };




class LlmTopics {
public:
    struct Options {
        QString modelPath = "res/qwen2.5-0.5b-instruct-q4_k_m.gguf";
        int32_t n_ctx = 2048;
        int32_t n_threads = 0;
        int32_t max_tokens = 512;
    };

    LlmTopics() = default;
    explicit LlmTopics(const Options& o) : opt_(o) {}
    ~LlmTopics();

    bool init();
    void destroy();

    // labels = список title из таблицы topic
    QVector<ScoredLabel> scoreLabels(const QString& text,
                                     const QStringList& labels,
                                     const QString& lang = "ru");

private:
    Options opt_;
    llama_model*   model_ = nullptr;
    llama_context* ctx_   = nullptr;
    const llama_vocab* vocab_ = nullptr;

    QString generate(const QString& prompt);
    static std::string toStd(const QString& s);
    static int detectThreads();
};
