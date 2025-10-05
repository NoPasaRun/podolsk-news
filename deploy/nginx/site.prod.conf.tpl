server {
  listen 80;
  listen [::]:80;
  server_name {{SERVER_NAME}};

  # Если используешь certbot nginx-плагин, он добавит /.well-known сам
  location /.well-known/acme-challenge/ { root /var/www/certbot; }

  return 301 https://$host$request_uri;
}

server {
  listen 443 ssl http2;
  listen [::]:443 ssl http2;
  server_name {{SERVER_NAME}};

  # ---- TLS ----
  ssl_certificate     /etc/letsencrypt/live/{{SERVER_NAME}}/fullchain.pem;
  ssl_certificate_key /etc/letsencrypt/live/{{SERVER_NAME}}/privkey.pem;
  ssl_session_timeout 1d;
  ssl_session_cache shared:SSL:10m;
  ssl_protocols TLSv1.2 TLSv1.3;
  ssl_prefer_server_ciphers on;
  ssl_stapling on;
  ssl_stapling_verify on;

  # (опционально) HSTS — включай, когда всё стабильно на HTTPS
  # add_header Strict-Transport-Security "max-age=31536000; includeSubDomains" always;

  # ---- Статика SPA ----
  root {{FRONT_ROOT}};   # ПУТЬ К ТВОЕМУ БИЛДУ

  # агрессивный кеш для fingerprinted-ассетов
  location ~* \.(?:js|css|png|jpg|jpeg|gif|svg|ico|woff2?)$ {
    try_files $uri =404;
    access_log off;
    add_header Cache-Control "public, max-age=31536000, immutable";
  }

  # SPA роутинг без петель
  location / {
    try_files $uri $uri/ /index.html =404;
  }

  # ---- API → backend (loopback, без наружного порта) ----
  # Поменяй порт на тот, что проброшен из compose на 127.0.0.1
  location /api/ {
    proxy_pass http://127.0.0.1:{{BACKEND_HOST_PORT}}/;   # <-- твой BACKEND_HOST_PORT
    proxy_http_version 1.1;
    proxy_set_header Host $host;
    proxy_set_header X-Real-IP $remote_addr;
    proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
    proxy_set_header X-Forwarded-Proto https;
    proxy_set_header X-Forwarded-Prefix /api;
  }

  # gzip (бонус)
  gzip on;
  gzip_types text/plain text/css application/json application/javascript application/xml image/svg+xml;
}
