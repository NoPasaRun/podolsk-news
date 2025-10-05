# syntax=docker/dockerfile:1.6

# ===== Builder =====
FROM debian:12 AS builder
ENV DEBIAN_FRONTEND=noninteractive

RUN apt-get update && apt-get install -y --no-install-recommends \
  build-essential cmake pkg-config git \
  libboost-dev libboost-system-dev libboost-thread-dev \
  libboost-regex-dev libboost-context-dev libboost-coroutine-dev \
  qt6-base-dev qt6-base-dev-tools \
  libcurl4-openssl-dev libxml2-dev ca-certificates \
  libgomp1 \
  && rm -rf /var/lib/apt/lists/*

WORKDIR /src
COPY CMakeLists.txt .
COPY include ./include
COPY src ./src
COPY res ./res
COPY feedpplib ./feedpplib
COPY llama.cpp ./llama.cpp

# просто копируем каталог моделей из контекста (может быть пустым)
COPY models/ /src/models/

# статическая сборка ggml/llama, чтобы не таскать .so
RUN cmake -S . -B /build -DCMAKE_BUILD_TYPE=Release -DBUILD_SHARED_LIBS=OFF -DGGML_OPENMP=ON \
 && cmake --build /build -j

# ===== Runtime =====
FROM debian:12 AS runner
ENV DEBIAN_FRONTEND=noninteractive

RUN apt-get update && apt-get install -y --no-install-recommends \
    libqt6core6 libqt6sql6 libqt6sql6-psql \
    libstdc++6 libgcc-s1 \
    libcurl4 libxml2 \
    ca-certificates tzdata \
    libgomp1 \
 && rm -rf /var/lib/apt/lists/*

WORKDIR /app
RUN mkdir -p /app/bin
COPY --from=builder /build/PodlskParcer /app/bin/PodlskParcer
RUN chmod +x /app/bin/PodlskParcer

COPY --from=builder /src/res    /app/res
COPY --from=builder /src/models /app/models

ENTRYPOINT ["/app/bin/PodlskParcer"]
