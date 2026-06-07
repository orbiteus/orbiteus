# 17 — Deployment

## Two compose files

| File | Purpose | Profile defaults |
|---|---|---|
| `docker-compose.yml` | Dev / general use | postgres+pgvector, redis, backend (uvicorn reload), admin-ui (:3000), portal-ui (:3001, next dev) |
| `docker-compose.prod.yml` | Single-host production | adds nginx, pgbouncer, gunicorn, celery worker + beat, portal-ui, certbot |

Both files share the same images. Profiles toggle optional services
(`worker`, `portal`, `flower`).

## Production services

```
nginx              # TLS + static cache + SSE-friendly buffering off
postgres           # pgvector/pgvector:pg16
pgbouncer          # transaction pooling
redis              # cache + pubsub + broker + jti revocation
migrate            # one-shot alembic upgrade head (depends_on: db, condition: service_completed_successfully)
backend            # gunicorn + UvicornWorker (N workers per replica)
worker             # celery -A celery_app worker -Q default,outbox,ai
beat               # celery -A celery_app beat (singleton)
admin-ui           # next start (output: standalone)
portal-ui          # next start
```

## Production HTTP server

```
gunicorn api:app \
  --workers $(nproc) * 2 + 1 \
  --worker-class uvicorn.workers.UvicornWorker \
  --bind 0.0.0.0:8000 \
  --max-requests 10000 --max-requests-jitter 1000 \
  --timeout 60 --graceful-timeout 30 --keep-alive 30 \
  --access-logfile - --error-logfile -
```

Uvicorn worker uses uvloop and httptools for performance.

## nginx essentials

- TLS with Let's Encrypt (certbot).
- HTTP→HTTPS redirect on `:80`.
- Static caching for `/_next/static/**` (`immutable, max-age=31536000`).
- `proxy_buffering off` for `/api/realtime/` (see `11-realtime.md`).
- `client_max_body_size` aligned with `MAX_FILE_SIZE_MB`.
- `proxy_read_timeout 1h` for SSE.

## Environment variables (prod)

Required:

- `DATABASE_URL`
- `SECRET_KEY` (JWT signing; generate with `openssl rand -hex 32`)
- `AI_SECRET_KEY` (Fernet key; generate with
  `python -c "from cryptography.fernet import Fernet; print(Fernet.generate_key().decode())"`)
- `REDIS_URL`
- `BOOTSTRAP_ADMIN_EMAIL`
- `BOOTSTRAP_ADMIN_PASSWORD` (must be rotated on first login)
- `ENVIRONMENT=production`
- `DEBUG=false`
- `CORS_ORIGINS` (JSON list)

Optional:

- `ATTACHMENT_STORAGE` (default `local`; S3-compatible backend post-v1)
- `ATTACHMENT_STORAGE_PATH` (default `/var/orbiteus/attachments` in prod compose)
- `ATTACHMENT_MAX_BYTES` (default `52428800` — 50 MiB)
- `RATE_LIMIT_TENANT_PER_MINUTE`
- `RATE_LIMIT_USER_PER_MINUTE`

## Scaling envelope (single host, "feels like home")

| Resource | 4 vCPU / 16 GB | 8 vCPU / 32 GB | 16 vCPU / 64 GB |
|---|---|---|---|
| Concurrent users (active) | ~1 000 | ~3 000 | ~6 000+ |
| RPS sustained | ~300 | ~800 | ~2 000 |
| Open SSE | ~5 000 | ~15 000 | ~40 000 |

Beyond ~10k DAU, plan migration in `32-multi-host-migration.md`.

## Healthchecks

- Liveness: `GET /api/health/live` — process up, no DB touch.
- Readiness: `GET /api/health/ready` — DB + Redis ping; `503` until both pass.
- Compose `healthcheck:` defined for db, redis, backend, workers.

## Rolling restarts

Single-host compose does not provide native rolling deploys. Two patterns:

1. **Blue-green** — start a parallel `backend2` service on a different port,
   flip nginx upstream, drain the old one. Works without orchestrator.
2. **Tolerate brief downtime** — fine for many B2B deployments; combine with
   `maintenance.html` page in nginx during deploy.

Multi-host = Kubernetes (see `32-multi-host-migration.md`).

## Backups

- `pg_dump` cron in a separate `backup` service writing to S3-compatible
  storage (Wasabi / Backblaze / R2).
- Daily full + hourly WAL when `pgbackrest` is enabled.
- Retention default: 30 days hourly + 365 days daily.

See `31-backups-and-dr.md`.

## Demo deployment

The demo on `demo.orbiteus.com` uses `docker-compose.demo.yml` (a thin variant
of prod with a single replica per service and bootstrap creds shown on the
welcome page via `NEXT_PUBLIC_DEMO_LOGIN_*` build args). Production deployments
must NOT pass those build args.

| Service | Image / notes |
|---|---|
| `db` | `pgvector/pgvector:pg16` — required for Alembic migrations that enable the `vector` extension |
| `redis` | `redis:7-alpine` — RBAC cache invalidation and rate limiting (`REDIS_URL=redis://redis:6379/0`) |
| `backend` | `Dockerfile.prod`; depends on healthy `db` + `redis` |
| `frontend` | `admin-ui/Dockerfile.prod`; published on host `127.0.0.1:13100` for nginx |

Deploy from a release tag (e.g. `v1.1.1`): `git fetch --tags && git checkout v1.1.1`,
then `docker compose --env-file .env.demo -f docker-compose.demo.yml up -d --build`.

