#pragma once
#include <string>
#include <vector>
#include <mutex>

struct TopicScore {
    std::string title;
    double score = 0.0;
};

class LlmTopics {
public:
    LlmTopics();
    ~LlmTopics();

    // Инициализируем модель (один раз на процесс).
    // modelPath можно оставить пустым — возьмём из дефайна LLM_MODEL_PATH_STR или из окружения.
    bool init(const std::string& modelPath = "");

    // Классифицирует текст статьи/кластера -> список (topic, score)
    // topics — список возможных тем (обязателен).
    // Возвращает до topK тем (по убыванию score), отфильтрованных порогом minScore.
    std::vector<TopicScore> classify(
        const std::string& text,
        const std::vector<std::string>& topics,
        int topK = 3,
        double minScore = 0.25
    );

private:
    bool ensureInit();
    std::string run(const std::string& prompt, int maxTokens = 128);

    // Вспомогалка: жёсткий JSON-промпт
    std::string makePrompt(const std::string& text, const std::vector<std::string>& topics);

private:
    // llama.cpp объекты
    struct Impl;
    Impl* impl_ = nullptr;

    // Простая защита (один контекст, один поток)
    std::mutex mtx_;
};
