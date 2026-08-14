# Product & Architecture Principles — Ozhzo Verse

These principles are non-negotiable architectural, engineering, and design laws that govern all technical and product decisions in Ozhzo Verse.

---

## 1. The Home is a First-Class Entity
- In traditional applications, data belongs directly to an individual User account.
- In Ozhzo Verse, **the Home is the primary organizational root**. Tasks, inventories, lists, bills, and events belong to a `Home`, not to an isolated user.
- All domain operations evaluate context in the realm of `home_id`.

## 2. Users Belong to Homes
- Users exist as independent identity records, but interact with domain data strictly through their membership in one or more Homes.
- A user account can be deactivated or deleted without corrupting the historical record or integrity of the Home data.

## 3. A User May Belong to Multiple Homes
- Architecture must support multi-home memberships from Day 1 (e.g., "Primary Family Home", "Vacation House", "Parental Home").
- The client and backend must support seamless active-home context switching without requiring re-authentication.

## 4. Strict Home Data Isolation
- Multi-tenancy is enforced at the database and application layer by scoping all queries with `home_id`.
- Under no circumstances should data from Home A leak into Home B.
- Compound database indexes must prefix `home_id` to guarantee both query isolation and performance.

## 5. Permissions are Home-Specific
- A user's role and capabilities are evaluated strictly within the context of the active `home_id`.
- A user might be an **Owner** in Home A, but a read-only **Member** in Home B. Global super-roles do not exist in the home domain.

## 6. Business Rules Must Not be Buried Inside UI Code
- Frontend applications (Next.js, Flutter) are strictly presentation, user interaction, and client-state layers.
- All validation, authorization checks, state transitions, recurring calculations, and business invariants live inside the backend domain service layer.

## 7. APIs Must Be Explicitly Documented
- No endpoint shall be deployed without an accurate OpenAPI (Swagger) contract specification.
- API models must use strongly typed DTOs (Pydantic models in FastAPI).

## 8. Database Migrations Must Be Version-Controlled
- Manual modifications to the database schema are strictly forbidden.
- All DDL changes must be generated as reversible, tested Alembic migrations stored in version control.

## 9. Secrets Must Never Be Hardcoded
- API keys, database credentials, encryption keys, and tokens must only be supplied via environment variables or secret managers.
- Continuous integration must enforce secret scanning.

## 10. Future Features Must Not Unnecessarily Complicate MVP
- Every abstraction introduces maintenance overhead.
- Code should be clean, modular, and adhere to SOLID principles, but we will not build speculative abstractions or database tables for unapproved post-MVP features (e.g., no IoT device registry tables in MVP).

## 11. Do Not Introduce Dependencies Without Justification
- Every library or package added to `pyproject.toml`, `package.json`, or `pubspec.yaml` increases supply-chain risk and bundle size.
- Evaluate standard library solutions first before adding third-party dependencies.

## 12. Do Not Make Product Decisions Silently
- Assumptions regarding business logic, edge cases, pricing, or permission boundaries must be documented in `/docs` and escalated for stakeholder alignment.

## 13. Never Rewrite Working Code Unnecessarily
- Refactoring must have clear performance, maintainability, or architectural objectives.
- Working, tested code must not be churned for cosmetic preferences.

## 14. Security and Privacy are Fundamental
- Household data includes intimate daily routines, inventory, family calendars, and financial bills.
- Data must be encrypted in transit (TLS 1.3) and at rest (AES-256). Passwords must use Argon2id / bcrypt hashing.

## 15. The `/docs` Directory is the Source of Truth
- If the code diverges from `/docs`, either the code is defective or the documentation must be updated via an architectural review.
- Architectural design documents precede implementation.
