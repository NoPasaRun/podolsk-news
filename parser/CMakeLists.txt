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

find_package(Qt6 REQUIRED COMPONENTS Core Sql)

add_subdirectory(feedpplib)
# исполняемый файл

file(GLOB_RECURSE SRC_FILES "${CMAKE_CURRENT_SOURCE_DIR}/src/*.cpp")
file(GLOB_RECURSE HEADER_FILES "${CMAKE_CURRENT_SOURCE_DIR}/include/*.hpp") #for qt
add_executable(${PROJECT_NAME} ${SRC_FILES} ${HEADER_FILES})

target_include_directories(${PROJECT_NAME} PRIVATE ${CMAKE_CURRENT_SOURCE_DIR}/include)

target_link_libraries(${PROJECT_NAME}
    PRIVATE feedpp
    PRIVATE Qt6::Core
    PRIVATE Qt6::Sql
)

add_custom_target(copy_resources ALL
    COMMAND ${CMAKE_COMMAND} -E copy_directory
        ${CMAKE_SOURCE_DIR}/res $<TARGET_FILE_DIR:${PROJECT_NAME}>/res
)

get_target_property(_autogen_dir ${PROJECT_NAME} AUTOGEN_BUILD_DIR)
if(_autogen_dir)
  target_include_directories(${PROJECT_NAME} PRIVATE "${_autogen_dir}/include")
endif()