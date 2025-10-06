# ===== Builder =====
FROM debian:12 AS builder
ENV DEBIAN_FRONTEND=noninteractive

# --- параметры модели (не скачиваем, ты уже кладёшь локально в /src/models) ---
ARG MODEL_REPO=Qwen/Qwen2.5-0.5B-Instruct-GGUF
ARG MODEL_FILE=qwen2.5-0.5b-instruct-q4_k_m.gguf
ARG MODEL_SHA256=""

RUN apt-get update && apt-get install -y --no-install-recommends \
  build-essential cmake pkg-config git ca-certificates curl \
  qt6-base-dev qt6-base-dev-tools \
  libqt6sql6-psql libpq-dev \
  libcurl4-openssl-dev libxml2-dev \
  libboost-dev libboost-system-dev libboost-thread-dev \
  libboost-regex-dev libboost-context-dev libboost-coroutine-dev \
  && rm -rf /var/lib/apt/lists/*

RUN update-ca-certificates

# 1) hiredis (без TLS)
WORKDIR /tmp
RUN git clone --depth 1 https://github.com/redis/hiredis.git
RUN cmake -S hiredis -B hiredis/build \
      -DCMAKE_BUILD_TYPE=Release \
      -DENABLE_SSL=OFF \
 && cmake --build hiredis/build -j \
 && cmake --install hiredis/build

# 2) redis-plus-plus (без TLS)
RUN git clone --depth 1 https://github.com/sewenew/redis-plus-plus.git
RUN cmake -S redis-plus-plus -B redis-plus-plus/build \
      -DREDIS_PLUS_PLUS_BUILD_TEST=OFF \
      -DREDIS_PLUS_PLUS_BUILD_SHARED=ON \
      -DREDIS_PLUS_PLUS_CXX_STANDARD=17 \
      -DREDIS_PLUS_PLUS_USE_TLS=OFF \
      -DCMAKE_BUILD_TYPE=Release \
      -DCMAKE_PREFIX_PATH="/usr/local/lib/cmake" \
 && cmake --build redis-plus-plus/build -j \
 && cmake --install redis-plus-plus/build

# 3) проект
WORKDIR /src
COPY CMakeLists.txt .
COPY include ./include
COPY src ./src
COPY res ./res
COPY feedpplib ./feedpplib
COPY llama.cpp ./llama.cpp

# локальная папка моделей (у тебя уже есть файл внутри)
COPY models/ /src/models/

# 4) сборка
RUN cmake -S . -B /build \
      -DCMAKE_BUILD_TYPE=Release \
      -DCMAKE_PREFIX_PATH="/usr/local/lib/cmake" \
 && cmake --build /build -j

# 5) собрать llama/ggml so-шки, чтобы положить их в рантайм
RUN set -eux; \
    mkdir -p /opt/llama-libs; \
    # ищем в папке сборки (и на всякий случай в /usr/local/lib)
    find /build -type f \( -name 'libllama.so*' -o -name 'libggml*.so*' -o -name 'libggml_*.so*' \) -exec cp -v {} /opt/llama-libs/ \; || true; \
    find /usr/local/lib -type f \( -name 'libllama.so*' -o -name 'libggml*.so*' -o -name 'libggml_*.so*' \) -exec cp -v {} /opt/llama-libs/ \; || true; \
    ls -l /opt/llama-libs || true

# ===== Runtime =====
FROM debian:12 AS runner
ENV DEBIAN_FRONTEND=noninteractive

ARG MODEL_FILE=qwen2.5-0.5b-instruct-q4_k_m.gguf

RUN apt-get update && apt-get install -y --no-install-recommends \
    libqt6core6 libqt6sql6 libqt6sql6-psql \
    libstdc++6 libgcc-s1 \
    libcurl4 libxml2 \
    ca-certificates tzdata \
    libgomp1 \
 && rm -rf /var/lib/apt/lists/*

WORKDIR /app

# системные либы
COPY --from=builder /usr/local/lib/libhiredis*.so* /usr/local/lib/
COPY --from=builder /usr/local/lib/libredis++.so* /usr/local/lib/

# llama/ggml либы из билдера
COPY --from=builder /opt/llama-libs/ /usr/local/lib/

# пусть динамические либы подхватятся
ENV LD_LIBRARY_PATH=/usr/local/lib:$LD_LIBRARY_PATH
RUN ldconfig

# бинарь + ресурсы + модели
RUN mkdir -p /app/bin
COPY --from=builder /build/PodlskParcer /app/bin/PodlskParcer
RUN chmod +x /app/bin/PodlskParcer

COPY --from=builder /src/res    /app/res
COPY --from=builder /src/models /app/models

# путь к модели для LlmTopics
ENV LLM_MODEL_PATH=/app/models/${MODEL_FILE}

ENTRYPOINT ["/app/bin/PodlskParcer"]
