# Music Memo homeserver Docker runbook

## 1. Подготовить `.env`

На homeserver в папке проекта:

```bash
cp .env.example .env
```

Заполнить:

```env
POSTGRES_PASSWORD=<strong-password>
POSTGRES_URL=postgresql://music_memo:<same-strong-password>@db:5432/music_memo

SPOTIFY_CLIENT_ID=<spotify-client-id>
SPOTIFY_CLIENT_SECRET=<spotify-client-secret>
SPOTIFY_REDIRECT_URI=https://musicmemo.<tailnet>.ts.net/api/auth/callback

FRONTEND_ORIGIN=https://musicmemo.<tailnet>.ts.net
API_BASE_URL=/api
FRONTEND_USER_ID=1
WEB_PORT=8080
```

`SPOTIFY_REDIRECT_URI` должен один в один совпадать с redirect URI в Spotify Developer Dashboard.

## 2. Запустить контейнеры

```bash
docker compose up -d --build
docker compose ps
```

Локальная проверка на homeserver:

```bash
curl http://127.0.0.1:8080/healthz
curl http://127.0.0.1:8080/api/health
```

## 3. Опубликовать через Tailscale Serve

На homeserver:

```bash
tailscale serve --bg 8080
tailscale serve status
```

После этого приложение должно открываться внутри tailnet:

```text
https://musicmemo.<tailnet>.ts.net
```

## 4. Проверить Spotify

В Spotify Developer Dashboard добавить:

```text
https://musicmemo.<tailnet>.ts.net/api/auth/callback
```

Потом открыть:

```text
https://musicmemo.<tailnet>.ts.net/api/auth/login
```

После успешного логина backend создаст пользователя в таблице `users`. Для текущего прототипа frontend использует `FRONTEND_USER_ID=1`; если созданный пользователь получил другой id, нужно поменять `FRONTEND_USER_ID` и пересобрать `web`:

```bash
docker compose build web
docker compose up -d web
```

## 5. Обновление

```bash
docker compose up -d --build
```

## 6. Остановка

```bash
docker compose down
```

Данные PostgreSQL останутся в Docker volume `music_memo_postgres_data`.
