# Источники библиотеки feedpp (без unitest.cpp!)
set(FEEDPP_SOURCES
    src/atom_parser.cpp
    src/exception.cpp
    src/date.cpp
    src/parser.cpp
    src/parser_factory.cpp
    src/rss_09x_parser.cpp
    src/rss_10_parser.cpp
    src/rss_parser.cpp
    src/utils.cpp
)

add_library(feedpp ${FEEDPP_SOURCES})

# Заголовки библиотеки
target_include_directories(feedpp
    PUBLIC
        ${CMAKE_CURRENT_SOURCE_DIR}/inc
)

# Зависимости
find_package(LibXml2 REQUIRED)
find_package(CURL REQUIRED)
# Если реально нужны эти компоненты Boost:
find_package(Boost 1.54 REQUIRED COMPONENTS system thread regex context coroutine)

target_link_libraries(feedpp
    PUBLIC
        LibXml2::LibXml2
        CURL::libcurl
        Boost::system
        Boost::thread
        Boost::regex
        Boost::context
        Boost::coroutine
)
