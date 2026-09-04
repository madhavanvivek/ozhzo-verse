# OZHZO VERSE — RELEASE MANAGEMENT & DEPLOYMENT PROCESS

---

## 1. Release Classification Taxonomy

Every change during the production pilot must be strictly classified:
1. **BUG FIX**: Fixes an identified functional defect or edge-case crash without altering data contracts.
2. **CONFIGURATION**: Environment variable, rate limit tuning, or alert threshold adjustment.
3. **UX IMPROVEMENT**: Non-breaking visual, copy, or accessibility refinement.
4. **PERFORMANCE FIX**: Index optimization, query streamlining, or asset bundling improvement.
5. **SECURITY FIX**: Immediate vulnerability remediation or credential rotation.
6. **FEATURE REQUEST**: Non-emergency enhancement triaged for future milestones.

---

## 2. Release Gate Workflow

```
[ Code Change / Fix ]
         │
         ▼
[ 1. Frozen Baseline Verification ] ──► (Confirm Stages 1–6 contracts intact)
         │
         ▼
[ 2. Backend Pytest Regression ] ──► (100% pass on all 430+ tests)
         │
         ▼
[ 3. Frontend Next.js Production Build ] ──► (30/30 routes cleanly compiled)
         │
         ▼
[ 4. Full Playwright E2E Regression ] ──► (69/69 passed in headless Chromium)
         │
         ▼
[ 5. Pre-Deployment Backup Snapshot ] ──► (Encrypted DB snapshot + SHA-256)
         │
         ▼
[ 6. Blue-Green / Zero-Downtime Cutover ] ──► (Deploy new containers & run smoke tests)
```

---

## 3. Rollback Protocol

If the automated production smoke test fails post-cutover:
1. Immediately switch load balancer router to previous stable container tag (Deployment A).
2. Because all migrations are backward-compatible additive changes, Deployment A operates without database corruption.
3. Post incident report and quarantine failed commit.
