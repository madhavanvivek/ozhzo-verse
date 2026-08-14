# Ozhzo Verse — Home Management

## 1. Overview
A **Home** is the primary organizational tenant in Ozhzo Verse. Every household operation, member relationship, and module entitlement is strictly scoped to a single Home entity.

## 2. Home Creation & Properties
- **Name**: Household name (e.g. "Madhavan Residence").
- **Geographic Details**:
  - `country` (ISO 3166-1 alpha-2 code, e.g. `IN`, `US`, `AE`)
  - `state_province`
  - `district_city`
  - `postal_code`
- **Timezone**: IANA timezone (e.g. `Asia/Kolkata`, `America/New_York`).
- **Currency**: ISO 4217 3-letter currency code (e.g. `INR`, `USD`, `AED`).
- **Creator Assignment**: The user creating the Home is automatically granted the `HOME_ADMIN` role.
- **Default Seeding**: Upon creation, default household inventory categories (`Pantry`, `Fridge`, `Freezer`, `Cleaning`, `Medicine`, `Other`) are provisioned automatically.

## 3. Home Endpoints
- `POST /api/v1/homes`: Creates a new Home.
- `GET /api/v1/homes`: Returns all Homes the authenticated user belongs to.
- `GET /api/v1/homes/{home_id}`: Retrieves comprehensive Home profile and statistics.
- `PATCH /api/v1/homes/{home_id}`: Modifies Home settings (requires `HOME_ADMIN`).
- `DELETE /api/v1/homes/{home_id}`: Soft-deletes / archives Home workspace (requires `HOME_ADMIN`).
