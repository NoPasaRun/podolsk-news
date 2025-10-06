# -------- .env autoload --------
ifneq (,$(wildcard .env))
  include .env
  export
endif

# -------- Defaults (fallbacks if .env is missing) --------
POSTGRES_USER	?=	postgres
POSTGRES_PASSWORD	?=	password
POSTGRES_DB	?=	postgres
REDIS_URL	?=	redis://redis:6379/0
PUBLIC_ORIGIN	?=	http://localhost
SUMMARIZER_MODEL	?=	textrank
VITE_API_BASE	?=	/api

PROJECT	?=	podolsk-news
SERVER_NAME	?=	localhost
FRONT_ROOT	?=	/var/www/html
BACKEND_HOST_PORT	?=	8080
ENV	?=	dev


# -------- Phony targets --------
.PHONY: dev-up dev-down logs-be sh-be sh-fe \
        prod-up prod-down prod-logs fe-build logs-pa logs-tg \
        prod-nginx-disable prod-nginx-enable prod-nginx-cert ips

# -------- ENV (docker nginx + vite) --------
ips:
	@docker compose ps -q | xargs docker inspect -f '{{.Name}} -> {{range .NetworkSettings.Networks}}{{.IPAddress}}{{end}}'

dev-up:
	docker compose --profile $(ENV) up -d --build

dev-down:
	docker compose --profile $(ENV) down --remove-orphans

logs-be:
	docker compose logs -f backend

logs-pa:
	docker compose logs -f parser

logs-tg:
	docker compose logs -f telegram

sh-be:
	docker compose exec backend bash

sh-fe:
	docker compose exec frontend bash

# -------- PROD (host nginx, static frontend, dockerized API/DB) --------
prod-up:
	docker compose up -d --build

prod-down:
	docker compose down --remove-orphans

prod-logs:
	sudo journalctl -u nginx -f

# Собрать фронт и выложить статику в $(FRONT_ROOT)
fe-build:
	cd frontend && npm ci && npm run build
	@echo "✔ FRONT_ROOT updated: $(FRONT_ROOT)"

# Включить сайт в системном nginx (использует deploy/nginx/*.conf из проекта)
prod-nginx-enable:
	./scripts/nginx_enable_prod.sh "$(PROJECT)"

# Отключить сайт в системном nginx
prod-nginx-disable:
	./scripts/nginx_disable_prod.sh "$(PROJECT)"

# Установка сертификата
prod-nginx-cert:
	sudo certbot --nginx -d "$(SERVER_NAME)" --email example@gmail.com --agree-tos --redirect
