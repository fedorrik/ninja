#!/usr/bin/env bash
set -euo pipefail
# Fresh Debian 12/13 or Ubuntu 24.04+; run from the extracted source directory.
if [ "$(id -u)" -ne 0 ]; then echo 'Запустите: sudo bash deploy/install.sh [домен]'; exit 1; fi
SITE_DOMAIN="${1:-_}"
if [[ ! "$SITE_DOMAIN" =~ ^[A-Za-z0-9.-]+$ && "$SITE_DOMAIN" != '_' ]]; then echo 'Недопустимый домен'; exit 1; fi
APP_SOURCE="$(cd "$(dirname "$0")/.." && pwd)"
if [ -e /etc/systemd/system/game-night.service ]; then echo 'Сервис уже установлен. Используйте инструкцию обновления в README.md.'; exit 1; fi
apt-get update
apt-get install -y python3 nginx certbot python3-certbot-nginx
id game-night >/dev/null 2>&1 || useradd --system --home /opt/game-night --shell /usr/sbin/nologin game-night
install -d -m 755 /opt/game-night
cp -a "$APP_SOURCE/server.py" "$APP_SOURCE/games" "$APP_SOURCE/static" /opt/game-night/
chown -R root:root /opt/game-night
install -d -m 700 -o game-night -g game-night /var/lib/game-night
cat > /etc/systemd/system/game-night.service <<'UNIT'
[Unit]
Description=Game Night server
After=network.target
[Service]
Type=simple
User=game-night
Group=game-night
WorkingDirectory=/opt/game-night
Environment=HOST=127.0.0.1
Environment=PORT=8080
Environment=DATA_DIR=/var/lib/game-night
Environment=PYTHONDONTWRITEBYTECODE=1
ExecStart=/usr/bin/python3 /opt/game-night/server.py
Restart=on-failure
RestartSec=3
NoNewPrivileges=true
PrivateTmp=true
ProtectSystem=strict
ProtectHome=true
ReadWritePaths=/var/lib/game-night
UMask=0077
[Install]
WantedBy=multi-user.target
UNIT
cat > /etc/nginx/sites-available/game-night <<NGINX
server {
    listen 80;
    server_name $SITE_DOMAIN;
    client_max_body_size 16k;
    location / {
        proxy_pass http://127.0.0.1:8080;
        proxy_set_header Host \$http_host;
        proxy_set_header X-Forwarded-Proto \$scheme;
        proxy_read_timeout 20s;
    }
}
NGINX
# This installer targets an EMPTY VPS. Disable only the distro's default vhost.
if [ -L /etc/nginx/sites-enabled/default ]; then unlink /etc/nginx/sites-enabled/default; fi
ln -s /etc/nginx/sites-available/game-night /etc/nginx/sites-enabled/game-night
nginx -t
systemctl daemon-reload
systemctl enable --now game-night nginx
systemctl reload nginx
printf '\nГотово. Проверьте: systemctl status game-night\n'
if [ "$SITE_DOMAIN" != '_' ]; then printf 'Для HTTPS выполните: sudo certbot --nginx -d %s\n' "$SITE_DOMAIN"; else printf 'Откройте http://IP_СЕРВЕРА\n'; fi
