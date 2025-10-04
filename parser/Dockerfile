# ===== Builder =====
FROM debian:12 AS builder
ENV DEBIAN_FRONTEND=noninteractive

RUN apt-get update && apt-get install -y --no-install-recommends \
  libboost-dev libboost-system-dev libboost-thread-dev \
  libboost-regex-dev libboost-context-dev libboost-coroutine-dev \
  build-essential cmake pkg-config git \
  qt6-base-dev qt6-base-dev-tools \
  libqt6sql6-psql libpq-dev \
  libcurl4-openssl-dev libxml2-dev \
 && rm -rf /var/lib/apt/lists/*

WORKDIR /src
COPY CMakeLists.txt .
COPY include ./include
COPY src ./src
COPY res ./res
COPY feedpplib ./feedpplib

RUN cmake -S . -B /build -DCMAKE_BUILD_TYPE=Release \
 && cmake --build /build -j

# ===== Runtime =====
FROM debian:12 AS runner
ENV DEBIAN_FRONTEND=noninteractive

RUN apt-get update && apt-get install -y --no-install-recommends \
    libqt6core6 libqt6sql6 libqt6sql6-psql \
    libstdc++6 libgcc-s1 \
    libcurl4 libxml2 \
    ca-certificates tzdata \
 && rm -rf /var/lib/apt/lists/*

WORKDIR /app

# создаём папку и кладём бинарь внутрь с именем
RUN mkdir -p /app/bin
COPY --from=builder /build/PodlskParcer /app/bin/PodlskParcer
RUN chmod +x /app/bin/PodlskParcer

# ресурсы
COPY --from=builder /src/res /app/res

ENTRYPOINT ["/app/bin/PodlskParcer"]
