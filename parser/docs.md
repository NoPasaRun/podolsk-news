# Feed Plus Plus (feedpp) — документация

Лёгкая C++-библиотека для парсинга RSS/Atom-лент, выделенная из проекта Newsbeuter и адаптированная в виде самостоятельного модуля. Поддерживает RSS 0.91/0.92/0.94/1.0/2.0 и Atom 0.3/1.0. Использует **libcurl** для загрузки и **libxml2** для разбора XML.

---

## Установка и сборка

### Зависимости

* C++11-компилятор
* **libxml2** (dev-пакет)
* **libcurl** (dev-пакет)
* (опционально) **Boost.Regex**, если компилятор GNU C++ старее 4.9 — будет автоматически подключён и добавлен флаг `-DUSE_BOOST_REGEX`

### Вариант A: Autotools

```bash
# если нет configure — сгенерируйте
./autogen.sh
./configure
make
make check     # прогнать юнит-тесты
sudo make install
sudo ldconfig  # вероятно потребуется на Linux
```

### Вариант B: CMake

```bash
mkdir build && cd build
cmake ..
make
./unitest      # запустить тесты
```

### Как подключить в свой проект

Минимальная команда компоновки (если библиотека установлена в систему):

```bash
g++ -std=cpp11 your_app.cpp -lfeedpp -lcurl -lxml2
```

Или добавьте в CMake:

```cmake
target_link_libraries(your_app PRIVATE feedpp curl xml2)
```

Подключаемый заголовок «всё-в-одном»:

```cpp
#include <feedpp.h>
```

---

## Быстрый старт

Минимальный цикл: скачать ленту по URL и распечатать элементы.

```cpp
#include <iostream>
#include <feedpp.h>

int main() {
    feedpp::parser::global_init();   // инициализация libcurl/libxml2 (один раз на процесс)

    try {
        feedpp::parser p; // можно указать таймаут/UA/прокси см. ниже
        feedpp::feed f = p.parse_url("https://example.com/feed.xml");

        std::cout << "Feed: " << f.title << "\nURL: " << f.link << "\n\n";
        for (const auto& it : f.items) {
            std::cout << "- " << it.title << "\n  " << it.link << "\n  " << it.pubDate << "\n\n";
        }
    } catch (const ::exception& ex) {
        std::cerr << "Parse error: " << ex.what() << std::endl;
        return 1;
    }

    feedpp::parser::global_cleanup(); // очистка libcurl/libxml2
    return 0;
}
```

---

## API-обзор

### Пространство имён `feedpp`

#### Структуры данных (из `types.h`)

```cpp
enum version {
  UNKNOWN, RSS_0_91, RSS_0_92, RSS_1_0, RSS_2_0,
  ATOM_0_3, ATOM_1_0, RSS_0_94, ATOM_0_3_NONS, TTRSS_JSON, NEWSBLUR_JSON
};

struct item {
  std::string title, title_type;         // "text" | "html" и т.п.
  std::string link;
  std::string description, description_type;
  std::string author, author_email;
  std::string pubDate;                   // нормализованная строка даты (см. ниже)
  std::string guid; bool guid_isPermaLink = false;
  std::string enclosure_url, enclosure_type;
  std::string content_encoded;           // RSS content:encoded
  std::string itunes_summary;            // iTunes summary
  std::string base;                      // Atom xml:base
  std::vector<std::string> labels;       // метки (напр. Google Reader)
  time_t pubDate_ts;                     // используется для некоторых форматов
};

struct feed {
  std::string encoding;
  version     rss_version;
  std::string title, title_type, description, link, language;
  std::string managingeditor, dc_creator, pubDate;
  std::vector<item> items;
};
```

#### Парсер (`parser.h`)

```cpp
class parser {
public:
  // Настройка сетевых параметров
  parser(unsigned int timeout_seconds = 30,
         const char* user_agent = "FeedPP/0.5.0",
         const char* proxy = nullptr,
         const char* proxy_auth = nullptr,
         curl_proxytype proxy_type = CURLPROXY_HTTP);

  // Главные методы
  feed parse_url(const std::string& url,
                 CURL* external_curl = nullptr,
                 time_t lastmodified = 0,
                 const std::string& etag = "",
                 const std::string& cookie_cache = "");

  feed parse_buffer(const char* buffer, size_t size, const char* url = nullptr);
  feed parse_file(const std::string& path);

  // Метаданные, прочитанные из HTTP-заголовков ответа
  time_t get_last_modified() const; // Last-Modified
  const std::string& get_etag() const; // ETag

  // Глобальная инициализация/очистка (вызывайте 1 раз на процесс)
  static void global_init();
  static void global_cleanup();
};
```

> **Загрузка по сети.** `parse_url` использует libcurl: редиректы, gzip/deflate, cookies (если задан `cookie_cache`), таймаут, user-agent, прокси, а также **If-Modified-Since/If-None-Match**, если вы передадите свои `lastmodified`/`etag`. Можно передать внешний `CURL*`, чтобы настроить дополнительные опции (см. пример ниже).

#### Работа с датами (`date.h`)

```cpp
class date {
public:
  static bool validate(const std::string& s, const char* regex_literal);
  static std::string format(const std::string& s);
  static char* w3cdtf_to_tm(const std::string& s, struct tm* out);
};
```

* `format(...)` принимает строки дат в распространённых форматах (RFC 822/1123, W3C DTF, ISO 8601) и преобразует их к человекочитаемой строке на основе `std::asctime(...)`. Учитывайте, что эта строка:

  * зависит от текущей локали,
  * оканчивается переводом строки.
* `validate(...)` позволяет быстро проверить, что строка соответствует одному из поддержанных регэкспов (см. константы `REGEX_*` в `date.h`).

#### Исключения (`exception.h`)

```cpp
class exception : public std::exception {
public:
  exception(const std::string& errmsg = "", int errcode = 0);
  const char* what() const noexcept override;
};
```

Все ошибки парсинга и сетевого уровня пробрасываются как `::exception`. Код ошибки (если есть) включён в текст `what()`.

---

## Примеры кода

### 1) Разбор локального файла ленты

```cpp
#include <iostream>
#include <feedpp.h>

int main() {
    feedpp::parser::global_init();
    try {
        feedpp::parser p;
        feedpp::feed f = p.parse_file("data/rss20.xml");

        std::cout << f.title << " (" << f.link << ")\n\n";
        for (const auto& it : f.items) {
            std::cout << it.title << "\n"
                      << "  link: " << it.link << "\n"
                      << "  date: " << it.pubDate   // asctime-строка; содержит '\n'
                      ;
        }
    } catch (const ::exception& ex) {
        std::cerr << ex.what() << std::endl;
    }
    feedpp::parser::global_cleanup();
}
```

### 2) Загрузка по URL с кешированием (ETag/Last-Modified), cookies и кастомной настройкой SSL

```cpp
#include <iostream>
#include <feedpp.h>
#include <curl/curl.h>

int main() {
    feedpp::parser::global_init();

    // Сохраняем метаданные между запусками (упрощённо — в памяти):
    static time_t        last_modified = 0;
    static std::string   etag;

    try {
        feedpp::parser p(/*timeout*/ 20, /*UA*/ "MyApp/1.0");

        // Кастомный CURL, чтобы включить проверку сертификата:
        feedpp::curl_handle curl;                // RAII-обёртка из utils.h
        curl_easy_setopt(curl.ptr(), CURLOPT_SSL_VERIFYPEER, 1L);
        curl_easy_setopt(curl.ptr(), CURLOPT_SSL_VERIFYHOST, 2L);

        // Cookie-jar на диске позволит сохранять сессии
        const std::string cookie_jar = "cookies.txt";

        // Передаём наши last-modified/etag: сервер может ответить 304 Not Modified
        feedpp::feed f = p.parse_url(
            "https://example.com/feed.xml",
            curl.ptr(),
            last_modified,
            etag,
            cookie_jar
        );

        // Обновляем кеш-метаданные из ответа
        last_modified = p.get_last_modified();
        etag          = p.get_etag();

        std::cout << "Items: " << f.items.size() << "\n";
        for (const auto& it : f.items) {
            std::cout << "- " << it.title << " — " << it.link << "\n";
        }
    } catch (const ::exception& ex) {
        std::cerr << "Error: " << ex.what() << std::endl;
    }

    feedpp::parser::global_cleanup();
    return 0;
}
```

---

## Детали реализации и поведение

* **Поддерживаемые форматы:**

  * RSS 0.91/0.92/0.94/1.0/2.0
  * Atom 0.3/1.0 (включая `xml:base`, `content`, `summary`, `link rel="alternate"/"enclosure"`)
  * Поля расширений: `content:encoded`, iTunes `summary`, Media RSS `content/group` и т.д.

* **Кодировки.** `feed.encoding` берётся из XML-документа. Текстовые поля возвращаются уже декодированными libxml2.

* **HTTP-детали.** По умолчанию:

  * Следуются редиректы (до 10),
  * Поддерживается `gzip, deflate`,
  * При передаче `cookie_cache` — читаются/пишутся cookies,
  * Включён `CURLOPT_FAILONERROR`,
  * **Важно:** в текущей версии внутри `parse_url` отключена проверка SSL-сертификата (`CURLOPT_SSL_VERIFYPEER = 0`). Если вам нужна строгая проверка, используйте внешний `CURL*` и включите её (см. пример №2).

* **Прокси.** В конструкторе можно задать: адрес, тип (`CURLPROXY_HTTP/SOCKS4/SOCKS5/…`), метод аутентификации (через `proxy_auth`).

* **Парсинг дат.** `date::format(...)` нормализует много форматов в «asctime-строку» (наподобие `Tue Dec 30 07:20:00 2008\n`). Если нужна исходная дата без преобразования — читайте её напрямую из XML до вызовов `date::format(...)` или модифицируйте код.

* **Исключения.** Бросаются `::exception` при сетевых/парсинговых ошибках.

* **Инициализация.** В многопоточных приложениях вызывайте `parser::global_init()` один раз до первого использования (и `global_cleanup()` при завершении). Экземпляры `feedpp::parser` не разделяют состояние между потоками.

---

## Полезные утилиты (`utils.h`)

Некоторые функции общего назначения, которые могут пригодиться:

* `feedpp::absolute_url(base, relative)`: сформировать абсолютный URL.
* `feedpp::escape_url(s)` / `unescape_url(s)`
* `feedpp::join(vector<string>, sep)`
* `feedpp::tokenize(...)` и варианты (в т.ч. `tokenize_quoted`)

RAII-обёртка над `CURL*`:

```cpp
feedpp::curl_handle h;     // авто-init и auto-cleanup
CURL* raw = h.ptr();
```

---

## Сборка и тестирование

* Юнит-тесты находятся в `src/unitest.cpp` и покрывают базовые сценарии разбора RSS/Atom, а также валидацию форматов дат.
* CI-конфигурация доступна в `.travis.yml` (gcc/clang).

---

## Лицензия

Исходники библиотеки лицензированы под **MIT/X Consortium License** (см. `LICENSE` в репозитории). Отдельные файлы могут иметь собственные заголовки лицензий — соблюдайте их условия при повторном использовании.

---

## FAQ

**Нужно ли всегда вызывать `global_init/global_cleanup`?**
Да, это обёртки для инициализации libcurl/libxml2. Вызовите один раз на процесс до работы с парсером и один раз при завершении.

**Как включить строгую проверку SSL?**
Передайте свой `CURL*` в `parse_url(...)` и установите:

```cpp
curl_easy_setopt(curl, CURLOPT_SSL_VERIFYPEER, 1L);
curl_easy_setopt(curl, CURLOPT_SSL_VERIFYHOST, 2L);
```

**Как использовать HTTP-кеширование?**
Сохраните `parser.get_last_modified()` и `parser.get_etag()` после успешной загрузки и передавайте их в следующие вызовы `parse_url(...)`.

---

Если нужно, добавлю примеры под ваши конкретные требования (прокси с авторизацией, фильтрация элементов по дате/автору, интеграция с вашим билдом и т.п.).
