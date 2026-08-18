# Music Memo: homeserver deployment plan

## Цель проекта

Развернуть Music Memo на домашнем сервере как личное web/PWA-приложение для сохранения заметок к текущему треку Spotify.

Итоговое состояние:
- приложение открывается с телефона/ноутбука по локальному или публичному адресу;
- backend получает текущий трек из Spotify;
- frontend показывает текущий трек, настроение и поле заметки;
- заметки сохраняются в PostgreSQL;
- данные переживают перезапуск сервера;
- есть понятный способ обновления, резервного копирования и восстановления.

## Текущее состояние

Проект находится в `/Users/ilia/dev/music_memo`.

Состав:
- Backend: FastAPI.
- Database: PostgreSQL через SQLAlchemy.
- Frontend: Vue 3 + Vite + PWA.
- Spotify OAuth: частично реализован.
- Docker Compose: сейчас описывает только PostgreSQL.

Ключевые файлы:
- `main.py` - запуск FastAPI.
- `database.py` - подключение к PostgreSQL.
- `models.py` - таблицы `users` и `entries`.
- `routers/auth.py` - Spotify OAuth и текущий трек.
- `routers/entries.py` - создание и чтение заметок.
- `frontend/src/MusicMemo.vue` - основной экран.
- `docker-compose.yml` - текущий PostgreSQL.

## Целевая архитектура на homeserver

Выбранный режим: Tailscale.

Рекомендуемый вариант для переноса:

```text
Browser / phone with Tailscale
      |
      | HTTPS
      v
https://<tailscale-machine>.<tailnet>.ts.net
      |
      v
Tailscale Serve on homeserver
      |
      v
Local reverse proxy, bound to 127.0.0.1:8080
      |
      +-- Frontend static files
      |
      +-- /api -> FastAPI backend
                 |
                 +-- PostgreSQL
                 |
                 +-- Spotify API
```

Минимальный вариант для первого переноса без отдельного reverse proxy:

```text
Browser / phone with Tailscale
      |
      | HTTPS
      v
Tailscale Serve on homeserver
      |
      +-- frontend container
      |
      +-- backend container
             |
             +-- PostgreSQL container
```

Для постоянного использования лучше идти к первому варианту: один HTTPS-адрес внутри tailnet, `/api` ведет в backend, база доступна только внутри Docker-сети, секреты лежат в `.env`.

## Требования к homeserver

Минимальные:
- Linux server: Debian/Ubuntu/Raspberry Pi OS/Proxmox VM/LXC.
- CPU: любой современный x86_64 или ARM64.
- RAM: от 1 GB, комфортно 2 GB+.
- Disk: от 5 GB свободного места, лучше 20 GB+ с учетом PostgreSQL и бэкапов.
- Docker и Docker Compose plugin.
- Доступ по SSH.

Желательные:
- статический локальный IP;
- Tailscale на homeserver и на устройствах, с которых открываем приложение;
- MagicDNS в Tailscale;
- HTTPS Certificates в Tailscale;
- reverse proxy: Caddy, Traefik, Nginx или Nginx Proxy Manager;
- регулярный backup директории данных PostgreSQL или SQL dump.

## Сетевые требования

Выбранный вариант: доступ через Tailscale.

Требования:
- homeserver должен быть подключен к tailnet;
- телефон/ноутбук тоже должны быть подключены к тому же tailnet;
- включить MagicDNS, чтобы устройство получило имя вида `<tailscale-machine>.<tailnet>.ts.net`;
- включить HTTPS Certificates в Tailscale, чтобы получить нормальный HTTPS URL;
- приложение не нужно публиковать в интернет через роутер;
- PostgreSQL не публикуем наружу;
- Docker reverse proxy публикуем только на `127.0.0.1:8080`;
- Tailscale Serve публикует локальный `127.0.0.1:8080` как HTTPS-сервис внутри tailnet.

Целевой URL приложения:

```text
https://<tailscale-machine>.<tailnet>.ts.net
```

Целевой Spotify callback:

```text
https://<tailscale-machine>.<tailnet>.ts.net/api/auth/callback
```

Пример, если устройство в Tailscale называется `musicmemo`:

```text
https://musicmemo.<tailnet>.ts.net
https://musicmemo.<tailnet>.ts.net/api/auth/callback
```

Важно: Spotify OAuth чувствителен к точному redirect URI. Адрес в Spotify Developer Dashboard должен совпадать с `SPOTIFY_REDIRECT_URI` один в один.

Также важно: Spotify требует HTTPS для redirect URI, кроме loopback-адресов. Поэтому для homeserver через Tailscale используем HTTPS-адрес `.ts.net`, а не `http://homeserver.local`.

## Переменные окружения

Нужны:

```env
POSTGRES_DB=music_memo
POSTGRES_USER=music_memo
POSTGRES_PASSWORD=<strong-password>
POSTGRES_URL=postgresql://music_memo:<strong-password>@db:5432/music_memo

SPOTIFY_CLIENT_ID=<from-spotify-dashboard>
SPOTIFY_CLIENT_SECRET=<from-spotify-dashboard>
SPOTIFY_REDIRECT_URI=https://<tailscale-machine>.<tailnet>.ts.net/api/auth/callback

FRONTEND_ORIGIN=https://<tailscale-machine>.<tailnet>.ts.net
API_BASE_URL=/api
```

Сейчас в проекте есть `.env.example`, но перед деплоем его лучше обновить под контейнерный запуск и не использовать `localhost` внутри backend-контейнера для PostgreSQL.

## Что нужно доработать перед переносом

Обязательные доработки:

1. Dockerfile для backend.
   - Установить Python-зависимости из `requirements.txt`.
   - Запускать `uvicorn main:app --host 0.0.0.0 --port 8000`.

2. Dockerfile или production build для frontend.
   - Собрать Vue через `npm run build`.
   - Отдавать `dist` через nginx/caddy или через общий reverse proxy.

3. Общий `docker-compose.yml`.
   - Сервисы: `db`, `api`, `frontend` или `proxy`.
   - Persistent volume для PostgreSQL.
   - `.env` для секретов.
   - Не публиковать PostgreSQL наружу без необходимости.
   - Публиковать web-вход только на `127.0.0.1:8080`, чтобы доступ шел через Tailscale Serve.

4. Настроить API URL во frontend.
   - Сейчас frontend жестко обращается к `http://localhost:8000`.
   - Нужно заменить на переменную окружения или относительный путь `/api`.

5. Убрать жесткий `user_id=1` из frontend.
   - Сейчас приложение работает как прототип.
   - Нужно после Spotify callback сохранять/получать реального пользователя.
   - Минимальный вариант: callback возвращает/редиректит с `user_id`.
   - Лучше: простая cookie/session token схема.

6. Настроить CORS безопаснее.
   - Сейчас разрешены все origins.
   - Для homeserver указать конкретный frontend origin.

7. Добавить healthcheck.
   - Например `GET /health`.
   - Упростит проверку после деплоя.

Желательные доработки:

1. Миграции базы.
   - Сейчас таблицы создаются через `Base.metadata.create_all`.
   - Для MVP допустимо, но для развития лучше Alembic.

2. Экран истории заметок.
   - API чтения уже есть, но frontend пока не показывает список сохраненных заметок.

3. Нормальная обработка ошибок.
   - Нет текущего трека.
   - Spotify token истек.
   - Пользователь не залогинен.
   - Backend недоступен.

4. Backup script.
   - `pg_dump` по расписанию.

5. Update script.
   - `git pull`, `docker compose build`, `docker compose up -d`.

## План переноса

### Шаг 1. Зафиксировать режим доступа

Режим выбран: Tailscale.

Рабочее решение:
- не открываем порты на роутере;
- не делаем публичный домен;
- используем приватный Tailscale HTTPS URL;
- Tailscale Serve проксирует локальный web-вход приложения;
- Spotify callback указывает на `.ts.net` HTTPS-адрес.

Нужно будет узнать два значения:
- имя устройства в Tailscale, например `musicmemo`;
- tailnet DNS suffix, например `<tailnet>.ts.net`.

### Шаг 2. Подготовить production-конфигурацию локально

Сделать:
- backend Dockerfile;
- frontend build;
- общий Compose;
- `.env.example` для homeserver;
- healthcheck;
- заменить `localhost:8000` во frontend.

Проверить локально:
- backend стартует;
- frontend открывается;
- backend видит PostgreSQL;
- OAuth login доходит до Spotify;
- заметка сохраняется в базу.

### Шаг 3. Подготовить Spotify app

В Spotify Developer Dashboard:
- создать или открыть существующее приложение;
- добавить redirect URI для Tailscale homeserver;
- записать `SPOTIFY_CLIENT_ID`;
- записать `SPOTIFY_CLIENT_SECRET`.

Для Tailscale пример:

```text
https://musicmemo.<tailnet>.ts.net/api/auth/callback
```

### Шаг 4. Подготовить homeserver

На сервере нужно:
- установить Tailscale;
- выполнить `sudo tailscale up`;
- убедиться, что сервер появился в Tailscale admin console;
- включить MagicDNS;
- включить HTTPS Certificates;
- выбрать стабильное имя устройства, например `musicmemo`;
- создать папку проекта, например `/opt/music-memo`;
- установить Docker;
- скопировать проект или подключить git remote;
- создать `.env`;
- поднять контейнеры;
- включить Tailscale Serve для локального web-входа;
- проверить логи.

Ожидаемая команда публикации после запуска Docker:

```bash
tailscale serve --bg 8080
```

Если web-вход будет слушать другой локальный порт, заменить `8080` на выбранный порт.

### Шаг 5. Запустить базу и приложение

Ожидаемый запуск:

```bash
docker compose up -d --build
docker compose ps
docker compose logs -f api
```

Проверки:
- API отвечает на `/health`;
- frontend открывается по `https://<tailscale-machine>.<tailnet>.ts.net`;
- login Spotify работает;
- текущий трек подтягивается;
- заметка сохраняется;
- после перезапуска контейнеров заметка остается.

### Шаг 6. Настроить backup

Минимально:
- daily `pg_dump`;
- хранить 7-30 последних копий;
- периодически проверять восстановление.

Что важно сохранить:
- PostgreSQL данные;
- `.env` отдельно и безопасно;
- исходники проекта или git remote.

### Шаг 7. Обновление проекта

Нужен простой процесс:

```bash
git pull
docker compose up -d --build
```

Если появятся миграции:

```bash
docker compose exec api alembic upgrade head
```

## Критерии готовности

Проект считается перенесенным, когда:
- приложение открывается с нужного адреса;
- Spotify login проходит успешно;
- текущий трек отображается;
- заметка с mood сохраняется;
- история заметок доступна через API или UI;
- данные сохраняются после перезапуска;
- есть backup;
- есть понятная инструкция обновления.

## Риски и решения

### Spotify callback не работает

Причина почти всегда в несовпадении redirect URI.

Решение:
- проверить `SPOTIFY_REDIRECT_URI` в `.env`;
- проверить redirect URI в Spotify Dashboard;
- убедиться, что схема `http/https`, домен, порт и путь совпадают.
- для Tailscale использовать HTTPS `.ts.net`, а не `localhost` или `homeserver.local`.

### Tailscale URL не открывается

Причины:
- устройство не подключено к tailnet;
- MagicDNS выключен;
- HTTPS Certificates выключены;
- `tailscale serve` не настроен или смотрит не на тот локальный порт;
- приложение не слушает `127.0.0.1:8080` на homeserver.

Решение:
- проверить `tailscale status`;
- проверить имя сервера в Tailscale admin console;
- проверить `tailscale serve status`;
- проверить локальный web-вход на homeserver: `curl http://127.0.0.1:8080`.

### Frontend не видит backend

Сейчас frontend использует `http://localhost:8000`, что на телефоне означает "сам телефон", а не homeserver.

Решение:
- перейти на относительный `/api`;
- или настроить `VITE_API_BASE_URL`.

### PostgreSQL недоступен из контейнера

В Docker Compose backend должен подключаться к host `db`, а не `localhost`.

Правильный пример:

```env
POSTGRES_URL=postgresql://music_memo:<password>@db:5432/music_memo
```

### Нет реального пользователя

Сейчас frontend сохраняет заметки для `user_id=1`.

Решение:
- на первом этапе можно вручную создать пользователя после OAuth;
- для нормального режима нужно связать frontend с auth flow и хранить текущего пользователя.

## Предлагаемый порядок нашей работы

1. Доработать проект под production Docker Compose.
2. Исправить API URL и `user_id=1`.
3. Добавить `/health`.
4. Проверить все локально.
5. Подготовить Tailscale на homeserver.
6. Включить MagicDNS и HTTPS Certificates.
7. Настроить Spotify redirect URI на `.ts.net`.
8. Перенести проект.
9. Запустить Docker Compose и Tailscale Serve.
10. Проверить приложение с телефона/ноутбука через Tailscale.
11. Добавить backup.
12. Дальше развивать UI: история заметок, поиск, фильтры, экспорт.
