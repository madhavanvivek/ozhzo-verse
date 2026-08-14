# Development Rules & Engineering Standards — Ozhzo Verse

## 1. Monorepo Structure & Organization

The codebase is organized as a unified monorepo:

```
ozhzo-verse/
├── docs/                 # Architectural source of truth
├── apps/
│   ├── web/              # Next.js 14+ TypeScript Web Application
│   └── mobile/           # Flutter Cross-Platform Mobile Application
├── services/
│   └── api/              # Python 3.12 + FastAPI Backend Service
├── packages/
│   ├── shared/           # Common utilities, constants, validation
│   └── types/            # Shared TypeScript interfaces & DTOs
├── infrastructure/       # Docker, CI/CD, deployment configs
├── database/             # PostgreSQL migrations & seed scripts
├── tests/                # E2E & Cross-service integration tests
└── scripts/              # Developer tooling & build scripts
```

---

## 2. Backend Coding Standards (Python + FastAPI)

1. **Python Version**: Python 3.12+ with strict type annotations.
2. **Framework**: FastAPI with asynchronous handlers (`async def`).
3. **ORM & Database**: SQLAlchemy 2.0 (async engine with `asyncpg`).
4. **Data Validation**: Pydantic v2 for all DTOs (Request / Response schemas).
5. **Code Style & Formatting**:
   - `ruff` for ultra-fast linting and code quality checks.
   - `black` for deterministic formatting (line length: 88 characters).
   - `mypy` with `--strict` type checking.
6. **Error Handling**: Raise domain-specific exceptions inheriting from `BaseDomainException` and map them to HTTP status codes via centralized FastAPI exception handlers.
7. **No Direct DB Queries in Routers**: Routers call Domain Services; Services call Repositories; Repositories query SQLAlchemy.

---

## 3. Web Frontend Standards (Next.js + TypeScript)

1. **Framework**: Next.js 14+ with App Router.
2. **Language**: TypeScript with strict mode enabled (`"strict": true`).
3. **Styling**: Vanilla CSS / CSS Modules with standard CSS Custom Properties referencing our Design System tokens. No arbitrary Tailwind utility clutter unless specifically structured.
4. **State Management**:
   - Server State: TanStack Query (React Query) for caching, optimistic updates, and background refetching.
   - Client / UI State: React Context or Zustand for local UI dialogs and home switcher state.
5. **Data Fetching**: Pure API client wrapper generated or structured around `@ozhzo/types`.
6. **No Business Rules in UI**: Do not perform financial math, date recurrence logic, or role permission validation solely on the client.

---

## 4. Mobile Standards (Flutter)

1. **SDK**: Flutter 3.x with Dart 3.x null safety.
2. **State Management**: Riverpod or Bloc for predictable, testable state transitions.
3. **Networking**: `dio` client with custom interceptors for Bearer Token injection and `X-Home-ID` header.
4. **Storage**: `flutter_secure_storage` for JWT tokens and sensitive keys.
5. **Architecture**: Feature-first folder structure (`features/inventory`, `features/tasks`).

---

## 5. Database Migration Rules (Alembic)

1. **Never mutate schema manually in production or staging**.
2. **All migrations must be reversible** (`upgrade()` and `downgrade()` functions implemented and verified).
3. **Zero-Downtime Safe DDL**:
   - Adding a column: Must be `NULLABLE` or have a safe `DEFAULT`.
   - Renaming a column: Multi-step deprecation (Add new -> backfill -> switch read -> switch write -> drop old).
4. **Tenant Isolation Column**: Every new domain table must include `home_id UUID NOT NULL REFERENCES homes(id) ON DELETE CASCADE`.

---

## 6. Git Workflow & Commit Conventions

### Branching Model:
- `main`: Production-ready, deployable code.
- `develop`: Integration branch for active sprint work.
- `feature/<module-name>`: Scoped feature branch (e.g., `feature/inventory-expiry-alerts`).
- `fix/<bug-description>`: Bug fix branch.

### Commit Format (Conventional Commits):
```text
feat(tasks): implement recurring chore generator service
fix(auth): correct refresh token expiry calculation
docs(api): add OpenAPI spec for bill settlement endpoint
refactor(inventory): optimize compound index for category queries
test(homes): add multi-tenant isolation unit tests
```

---

## 7. Security & Secret Hygiene

1. **Zero Hardcoded Secrets**: Under no circumstances should passwords, JWT secrets, database connection strings, or third-party API keys exist in git.
2. **Environment Configuration**: Loaded strictly via `.env` and validated at startup using Pydantic Settings (`BaseSettings`).
3. **Sanitization**: All user inputs sanitized to prevent SQL injection (handled via SQLAlchemy parameterized queries) and XSS (handled via React/Flutter escaping).
4. **Logging Privacy**: Never log plain-text passwords, tokens, full credit card numbers, or personally identifiable home member details.

---

## 8. Definition of Done (DoD) for MVP Features

A feature or task is only marked **Done** when:
1. Architectural documentation in `/docs` is updated (if API contracts or data models changed).
2. Backend domain service logic has unit test coverage (>80%).
3. Integration test verifies multi-tenant home isolation (`home_id` isolation test).
4. API endpoint is typed, documented in Swagger, and handles validation errors.
5. Frontend/Mobile UI handles Loading, Error, Empty, and Success states.
6. Linting, type checks (`mypy`, `tsc`), and automated tests pass in CI.
