# -------- .env autoload --------
ifneq (,$(wildcard .env))
  include .env
  export
endif

# -------- Defaults (fallbacks if .env is missing) --------
PROJECT      ?= my-news
SERVER_NAME  ?= news.example.com
FRONT_ROOT   ?= /srv/apps/$(PROJECT)/frontend_dist
API_UPSTREAM ?= 127.0.0.1:8000
DEV          ?= dev

# -------- Phony targets --------
.PHONY: dev-up dev-down logs-be be sh-be sh-fe \
        prod-up prod-down prod-logs fe-build \
        prod-nginx prod-nginx-disable prod-nginx-reload ips

# -------- DEV (docker nginx + vite) --------
ips:
	@docker compose ps -q | xargs docker inspect -f '{{.Name}} -> {{range .NetworkSettings.Networks}}{{.IPAddress}}{{end}}'

dev-up:
	docker compose --profile $(DEV) up -d --build

dev-down:
	docker compose --profile $(DEV) down

logs-be:
	docker compose logs -f backend

be:
	curl -s http://localhost/api/health | jq .

sh-be:
	docker compose exec backend bash

sh-fe:
	docker compose exec frontend bash

# -------- PROD (host nginx, static frontend, dockerized API/DB) --------
prod-up:
	docker compose up -d --build

prod-down:
	docker compose down

prod-logs:
	docker compose logs -f

# Собрать фронт и выложить статику в $(FRONT_ROOT)
fe-build:
	cd frontend && npm ci && npm run build
	@echo "→ syncing frontend/dist → $(FRONT_ROOT)"
	sudo mkdir -p "$(FRONT_ROOT)"
	# аккуратно очистим только содержимое каталога
	sudo bash -lc 'shopt -s dotglob nullglob; rm -rf "$(FRONT_ROOT)"/*'
	sudo cp -a frontend/dist/. "$(FRONT_ROOT)/"
	@echo "✔ FRONT_ROOT updated: $(FRONT_ROOT)"

# Включить сайт в системном nginx (использует deploy/nginx/*.conf из проекта)
prod-nginx:
	SERVER_NAME="$(SERVER_NAME)" FRONT_ROOT="$(FRONT_ROOT)" API_UPSTREAM="$(API_UPSTREAM)" \
	./scripts/nginx_enable_prod.sh "$(PROJECT)"

# Отключить сайт в системном nginx
prod-nginx-disable:
	./scripts/nginx_disable_prod.sh "$(PROJECT)"

# Проверка и reload nginx (хостовой)
prod-nginx-reload:
	sudo nginx -t && sudo systemctl reload nginx
