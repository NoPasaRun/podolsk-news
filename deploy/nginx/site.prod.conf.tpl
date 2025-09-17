server {
  listen 80;
  server_name {{SERVER_NAME}};

  root {{FRONT_ROOT}};
  index index.html;

  location / {
    try_files $uri /index.html;
  }

  location /api/ {
    proxy_pass http://{{API_UPSTREAM}}/api/;
    proxy_set_header Host $host;
    proxy_set_header X-Real-IP $remote_addr;
  }

  gzip on;
  gzip_types text/plain text/css application/json application/javascript;
}
