cmake_minimum_required(VERSION 3.21)

project(PodlskParcer
    VERSION 0.1
    DESCRIPTION "Minimal CMake project"
    LANGUAGES CXX)

set(CMAKE_AUTOMOC ON)
# set(CMAKE_AUTOUIC ON)
# set(CMAKE_AUTORCC ON)


# стандарт языка
set(CMAKE_CXX_STANDARD 17)
set(CMAKE_CXX_STANDARD_REQUIRED True)
set(CMAKE_EXPORT_COMPILE_COMMANDS ON CACHE INTERNAL "")

add_compile_options(-Wno-multichar)

# --- мини-скачивалка GGUF без лишних плясок ---
set(MODELS_DIR "${CMAKE_SOURCE_DIR}/models")
set(MODEL_FILE "qwen2.5-0.5b-instruct-q4_k_m.gguf")
set(MODEL_URL  "https://huggingface.co/Qwen/Qwen2.5-0.5B-Instruct-GGUF/resolve/main/${MODEL_FILE}")
set(MODEL_PATH "${MODELS_DIR}/${MODEL_FILE}")

file(MAKE_DIRECTORY "${MODELS_DIR}")

if(NOT EXISTS "${MODEL_PATH}")
  message(STATUS "Downloading ${MODEL_FILE} to ${MODELS_DIR} ...")
  # Если хочешь контроль целостности — добавь EXPECTED_HASH с SHA256
  file(DOWNLOAD
       "${MODEL_URL}"
       "${MODEL_PATH}"
       SHOW_PROGRESS
       TLS_VERIFY ON)
  message(STATUS "Model saved to ${MODEL_PATH}")
else()
  message(STATUS "Model already exists: ${MODEL_PATH}")
endif()

# чтобы код/скрипты могли взять путь:
set(LLM_MODEL_PATH "${MODEL_PATH}" CACHE FILEPATH "Path to GGUF model" FORCE)

find_package(Qt6 REQUIRED COMPONENTS Core Sql)
find_package(hiredis REQUIRED)
find_package(redis++ REQUIRED)


add_compile_options(-fopenmp)
add_link_options(-fopenmp)
set(GGML_OPENMP ON CACHE BOOL "" FORCE)  # чтобы отключить ворнинг внутри llama.cpp

add_subdirectory(feedpplib)
# исполняемый файл
add_subdirectory(llama.cpp)


file(GLOB_RECURSE SRC_FILES "${CMAKE_CURRENT_SOURCE_DIR}/src/*.cpp")
file(GLOB_RECURSE HEADER_FILES "${CMAKE_CURRENT_SOURCE_DIR}/include/*.hpp") #for qt
add_executable(${PROJECT_NAME} ${SRC_FILES} ${HEADER_FILES})

target_include_directories(${PROJECT_NAME}
    PRIVATE ${CMAKE_CURRENT_SOURCE_DIR}/include
    PRIVATE ${CMAKE_CURRENT_SOURCE_DIR}/llama.cpp
)

target_link_libraries(${PROJECT_NAME}
    PRIVATE feedpp
    PRIVATE Qt6::Core
    PRIVATE Qt6::Sql
    hiredis
    redis++
    PRIVATE llama
)

add_custom_target(copy_resources ALL
    COMMAND ${CMAKE_COMMAND} -E copy_directory
        ${CMAKE_SOURCE_DIR}/res $<TARGET_FILE_DIR:${PROJECT_NAME}>/res
)

get_target_property(_autogen_dir ${PROJECT_NAME} AUTOGEN_BUILD_DIR)
if(_autogen_dir)
  target_include_directories(${PROJECT_NAME} PRIVATE "${_autogen_dir}/include")
endif()