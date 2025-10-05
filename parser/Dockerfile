# ===== Builder =====
FROM debian:12 AS builder
ENV DEBIAN_FRONTEND=noninteractive

RUN apt-get update && apt-get install -y --no-install-recommends \
  build-essential cmake pkg-config git ca-certificates \
  qt6-base-dev qt6-base-dev-tools \
  libqt6sql6-psql libpq-dev \
  libcurl4-openssl-dev libxml2-dev \
  libboost-dev libboost-system-dev libboost-thread-dev \
  libboost-regex-dev libboost-context-dev libboost-coroutine-dev \
  && rm -rf /var/lib/apt/lists/*

RUN update-ca-certificates

# 1) hiredis (без TLS; если нужен TLS — см. ниже)
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

# 3) твой проект
WORKDIR /src
COPY CMakeLists.txt .
COPY include ./include
COPY src ./src
COPY feedpplib ./feedpplib
COPY llama.cpp ./llama.cpp
COPY models/ /src/models/

RUN cmake -S . -B /build \
      -DCMAKE_BUILD_TYPE=Release \
      -DCMAKE_PREFIX_PATH="/usr/local/lib/cmake" \
	&& cmake --build /build -j

COPY res ./res

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

# Кладём собранные библиотеки
COPY --from=builder /usr/local/lib/libhiredis*.so* /usr/local/lib/
COPY --from=builder /usr/local/lib/libredis++.so* /usr/local/lib/
RUN ldconfig

# бинарь + ресурсы
RUN mkdir -p /app/bin
COPY --from=builder /build/PodlskParcer /app/bin/PodlskParcer
RUN chmod +x /app/bin/PodlskParcer

COPY --from=builder /src/res    /app/res
COPY --from=builder /src/models /app/models

ENTRYPOINT ["/app/bin/PodlskParcer"]
