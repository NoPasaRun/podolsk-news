#pragma once
#include <QSet>
#include <QString>
#include <vector>
#include <string>

class DBManager;
struct TopicScore;

class TopicAssigner {
public:
    TopicAssigner(DBManager& db);
    ~TopicAssigner();

    // Проставить темы для набора кластеров
    void assignForClusters(const QSet<int>& clusterIds);

private:
    std::string buildClusterText(int clusterId, int limitArticles = 5);
    std::vector<std::string> topicList() const;

private:
    DBManager& db_;
};
