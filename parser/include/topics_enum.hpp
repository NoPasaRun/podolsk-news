#pragma once
#include <QString>
#include <QVector>

enum TopicId : int {
    T_Politics=1, T_Business, T_Tech, T_Science, T_Health, T_Sports,
    T_Entertainment, T_World, T_Local, T_Culture, T_Education, T_Travel,
    T_Auto, T_Finance, T_Real_estate, T_Crime, T_War, T_COUNT=17
};

static inline const char* kTopicLabelById[T_COUNT+1] = {
    "", // 0
    "Politics","Business","Tech","Science","Health","Sports",
    "Entertainment","World","Local","Culture","Education","Travel",
    "Auto","Finance","Real_estate","Crime","War"
};

struct TopicScore { int topic_id; double score; bool primary=false; };

static inline QVector<int> allTopicIds() {
    QVector<int> v; v.reserve(T_COUNT);
    for (int i=1;i<=T_COUNT;++i) v.push_back(i);
    return v;
}
