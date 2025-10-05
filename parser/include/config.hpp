#pragma once

#include <fstream>
#include <stdexcept>
#include <QString>
#include <QJsonDocument>
#include <QJsonObject>
#include <cstdlib>




class Config
{
public:    
    QJsonObject data;
    qint64 lazy_time = 60; // seconds по умолчанию
    QString db_address;
    qint64 db_port;
    QString db_name;
    QString db_user;
    QString db_password;
    QString path;

    Config()
    {
        
    }

    void parse(QString _path)
    {
        this->path = _path;
        readConfigFromFile(_path);
        
        lazy_time = data["lazy_time"].toInt();
        db_address = data["db_address"].toString();
        db_port = data["db_port"].toInteger();
        db_name = data["db_name"].toString();
        db_user = data["db_user"].toString();
        db_password = data["db_password"].toString();
        
        const char* host = std::getenv("POSTGRES_PASSWORD");
        if(host != nullptr)
            db_password = QString(host);
        else
            qWarning() << "Переменная окружения с паролем базы данных не обнаружена";

    }
    
private:
    void readConfigFromFile(QString path)
    {
        if(path.isNull()) throw std::runtime_error("config path empty");

        std::ifstream configFile(path.toStdString());
        if (!configFile.is_open()) {
            throw std::runtime_error("failed to open config file");
        }

        std::string content((std::istreambuf_iterator<char>(configFile)),
                             std::istreambuf_iterator<char>());
        QJsonDocument doc = QJsonDocument::fromJson(QByteArray(content.c_str(), static_cast<int>(content.size())));
        if (doc.isNull()) {
            throw std::runtime_error("failed to parse config JSON");
        }

        data = doc.object();
    }
};
