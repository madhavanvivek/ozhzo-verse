# Ozhzo Verse — Production Deployment Guide (DEPLOYMENT.md)

**Target Environment**: Production Linux / Kubernetes / Docker Compose  
**Stack**: Next.js 14+ (Web), FastAPI (Python 3.11+), PostgreSQL 16+, Redis 7+, Nginx Edge Proxy  

---

## 1. System Architecture & Topology

```mermaid
flowchart TD
    CLIENT[Web / Mobile Clients] -->|HTTPS :443| NGINX[Nginx Edge / Cloudflare]
    NGINX -->|HTTP :3000| NEXT[Next.js Web SSR Service]
    NGINX -->|HTTP :8000| API[FastAPI Core Backend Cluster]
    API -->|Async Connection Pool| PG[(PostgreSQL 16 Multi-Tenant DB)]
    API -->|Pub/Sub & Token Blacklist| REDIS[(Redis 7 Cluster)]
    API -->|S3 API| S3[(Encrypted Object Storage)]
```

---

## 2. Production Environment Variables & Secrets

Never commit production `.env` files to source control. Inject secrets via environment variables or secret managers (e.g. AWS Secrets Manager, HashiCorp Vault, Doppler).

### Backend (`services/api/.env.production`)
```ini
# Environment
ENVIRONMENT=production
DEBUG=false
LOG_LEVEL=INFO

# Networking & CORS
API_HOST=0.0.0.0
API_PORT=8000
ALLOWED_ORIGINS=https://app.ozhzo.com,https://api.ozhzo.com

# Security & Cryptography
# Generate with: openssl rand -base64 64
JWT_SECRET_KEY=ACTUAL_PRODUCTION_HIGH_ENTROPY_64_CHAR_SECRET_KEY
JWT_ALGORITHM=HS256
ACCESS_TOKEN_EXPIRE_MINUTES=15
REFRESH_TOKEN_EXPIRE_DAYS=30

# PostgreSQL Production Database (with SSL)
DATABASE_HOST=postgres.internal.ozhzo.com
DATABASE_PORT=5432
DATABASE_USER=ozhzo_prod_app
DATABASE_PASSWORD=STRONG_PROD_DB_PASSWORD
DATABASE_NAME=ozhzo_verse_prod
DATABASE_URL=postgresql+asyncpg://ozhzo_prod_app:STRONG_PROD_DB_PASSWORD@postgres.internal.ozhzo.com:5432/ozhzo_verse_prod?ssl=require
DATABASE_URL_SYNC=postgresql://ozhzo_prod_app:STRONG_PROD_DB_PASSWORD@postgres.internal.ozhzo.com:5432/ozhzo_verse_prod?ssl=require

# Redis Cache & PubSub
REDIS_HOST=redis.internal.ozhzo.com
REDIS_PORT=6379
REDIS_PASSWORD=STRONG_PROD_REDIS_PASSWORD
REDIS_URL=rediss://:STRONG_PROD_REDIS_PASSWORD@redis.internal.ozhzo.com:6379/0
```

### Web Client (`apps/web/.env.production`)
```ini
NODE_ENV=production
NEXT_PUBLIC_API_BASE_URL=https://api.ozhzo.com/api/v1
NEXT_PUBLIC_APP_ENV=production
```

---

## 3. Container Orchestration & Docker Build

### 3.1 Production Image Builds
```bash
# 1. Build Backend API Container
docker build -t ozhzo/api:v1.0.0 -f services/api/Dockerfile .

# 2. Build Web Client Container
docker build -t ozhzo/web:v1.0.0 -f apps/web/Dockerfile .
```

### 3.2 Production Nginx Configuration
Ensure HTTP $\rightarrow$ HTTPS redirection, TLS 1.3 encryption, and HSTS headers are enabled in `/etc/nginx/conf.d/default.conf`.

---

## 4. Database Migrations & Initialization

1. **Verify Database Connectivity**:
   ```bash
   pg_isready -h postgres.internal.ozhzo.com -p 5432 -U ozhzo_prod_app
   ```
2. **Apply Database Migrations**:
   ```bash
   cd services/api
   alembic upgrade head
   ```
3. **Verify Indexes**: Ensure compound indexes (`idx_inv_items_home_search`, `idx_tasks_home_search`, `idx_bills_home_search`, `idx_home_members_lookup`) are active.

---

## 5. CI/CD Deployment Pipeline (`.github/workflows/deploy.yml`)

1. **Test & Lint Quality Gate**: Executes `bash scripts/lint.sh` and `bash scripts/test.sh`.
2. **Build Docker Images**: Multi-stage docker builds with caching.
3. **Push to Container Registry**: Pushes signed images to AWS ECR / GitHub Packages.
4. **Zero-Downtime Rolling Deployment**:
   - Deploys new API pods/containers.
   - Waits for `/api/v1/health` readiness probe to report `{"status": "healthy"}`.
   - Switches load balancer traffic seamlessly.

---

## 6. Rollback Protocol

If critical anomalies occur post-deployment:
1. Revert load balancer to previous container image tag (`ozhzo/api:v0.9.9`).
2. If database migration needs rolling back: `alembic downgrade -1`.
3. Flush Redis token revocation caches if payload structural schemas changed.
