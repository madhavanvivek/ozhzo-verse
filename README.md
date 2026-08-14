# Ozhzo Verse

> **The Digital Operating System for Homes**

Ozhzo Verse elevates the **Home into a first-class digital entity**, providing a unified, collaborative, and intelligent operating platform for household members to coordinate daily chores, manage inventory, align on shopping, track finances, and maintain shared household memory.

---

## 1. Monorepo Structure

```text
ozhzo-verse/
├── docs/                 # Authoritative Architecture & Product Specifications
├── apps/
│   ├── web/              # Next.js 14+ TypeScript Web Application
│   └── mobile/           # Flutter Cross-Platform Mobile Application
├── services/
│   └── api/              # Python 3.12 + FastAPI Async Backend Service
├── packages/
│   ├── shared/           # Common utilities, constants, validation helpers
│   └── types/            # Shared TypeScript interfaces & DTOs
├── infrastructure/
│   └── docker/           # Docker Compose, Nginx gateway, multi-container orchestration
├── database/             # PostgreSQL migrations & seed definitions
├── tests/                # E2E & Cross-service integration test suites
└── scripts/              # Developer tooling (setup, build, test, lint, clean)
```

---

## 2. Technology Stack

- **Web**: Next.js 14+ (App Router), React 18, TypeScript, TanStack Query
- **Mobile**: Flutter 3.x, Dart 3.x
- **Backend Service**: Python 3.12, FastAPI, Pydantic v2, SQLAlchemy 2.0 Async
- **Database**: PostgreSQL 16 (Multi-Tenant by `home_id`, Asyncpg, Alembic)
- **In-Memory Cache**: Redis 7 (Session registry, rate-limiting, Pub/Sub live sync)
- **Infrastructure**: Docker, Nginx, MinIO / S3 Object Store

---

## 3. Quickstart & Local Development

### Prerequisites
- Node.js 20+ & npm / pnpm
- Python 3.12+
- Docker & Docker Compose

### 1. Initialize Environment
```bash
# Copy template environment variables
cp .env.example .env
cp .env.example services/api/.env
cp .env.example apps/web/.env.local
```

### 2. Launch with Docker (Full Stack)
```bash
# Start all containers (Postgres, Redis, MinIO, API, Web, Nginx)
docker-compose -f infrastructure/docker/docker-compose.yml up --build
```
- **Web App**: `http://localhost:3000`
- **FastAPI Documentation (Swagger)**: `http://localhost:8000/docs`
- **Health Check**: `http://localhost:8000/health/ready`

### 3. Local Development Scripts
```bash
# Run all tests
bash scripts/test.sh

# Run linting across all packages & services
bash scripts/lint.sh

# Build all monorepo targets
bash scripts/build.sh
```

---

## 4. Documentation & Specifications

All architectural decisions and specifications are documented under [`docs/`](./docs):
- [`PRODUCT_VISION.md`](./docs/PRODUCT_VISION.md)
- [`MVP_SCOPE.md`](./docs/MVP_SCOPE.md)
- [`USER_ROLES.md`](./docs/USER_ROLES.md)
- [`USER_JOURNEYS.md`](./docs/USER_JOURNEYS.md)
- [`PRD.md`](./docs/PRD.md)
- [`UX_ARCHITECTURE.md`](./docs/UX_ARCHITECTURE.md)
- [`ARCHITECTURE.md`](./docs/ARCHITECTURE.md)
- [`DATABASE_DESIGN.md`](./docs/DATABASE_DESIGN.md)
- [`API_DESIGN.md`](./docs/API_DESIGN.md)
- [`DESIGN_SYSTEM.md`](./docs/DESIGN_SYSTEM.md)
- [`DEVELOPMENT_RULES.md`](./docs/DEVELOPMENT_RULES.md)
- [`ROADMAP.md`](./docs/ROADMAP.md)
