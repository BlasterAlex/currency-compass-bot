# Деплой

## Локально

```bash
cp deploy/.env.example deploy/.env
# указать BOT_TOKEN
make dev
```

## VPS (`/opt/currency-compass-bot`)

1. На сервере положить `deploy/docker-compose.prod.yml` и создать `deploy/.env`.
2. В секретах GitHub добавить `VPS_HOST`, `VPS_USER`, `VPS_SSH_KEY`.
3. Разрешить VPS тянуть образ из GHCR (`ghcr.io/blasteralex/currency-compass-bot`).
4. Опубликовать GitHub Release - workflow соберёт образ и выполнит:

```bash
cd /opt/currency-compass-bot
docker compose -f deploy/docker-compose.prod.yml pull
docker compose -f deploy/docker-compose.prod.yml up -d
```

Postgres в prod слушает `127.0.0.1:5433`, чтобы не пересекаться с PriceStation на `5432`.

Алерты в Telegram собирает сервис `alerts`: [alerts/README.md](alerts/README.md).

## Чеклист первого запуска в прод

1. Создать бота в @BotFather и записать токен в `deploy/.env` как `BOT_TOKEN`.
2. На VPS: каталог `/opt/currency-compass-bot` с `deploy/docker-compose.prod.yml` и `deploy/.env`.
3. Секреты репозитория: `VPS_HOST`, `VPS_USER`, `VPS_SSH_KEY`.
4. Влить изменения в `main` и опубликовать GitHub Release.
5. В Telegram: `/start` → `/currencies` → добавить валюту → `/rate`.
