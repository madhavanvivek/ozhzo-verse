# OZHZO VERSE — PILOT OPERATIONS GUIDE

---

## 1. Pilot Overview & Objectives

The Private Pilot transitions Ozhzo Verse from synthetic testing to controlled real-world usage across:
- **Target Cohort**: 25–50 Households (approx. 100–200 Active Users).
- **Duration**: 4–8 Weeks of sustained daily household activity.
- **Key Focus**: Onboarding velocity, daily active usage, AI assistant engagement, automation utility, and support ticket triage.

---

## 2. Cohort Structure & Household Diversity

To ensure representative household patterns, the pilot includes:
1. **Nuclear Families (2 Parents + Kids)**: Focus on chores, shared calendars, shopping lists, and Child-safe permissions.
2. **Couples / Dual-Income Households**: Focus on shared bill splitting, recurring expense reminders, and subscription management.
3. **Shared Living / Roommates**: Focus on task assignment, inventory replenishment, and independent member roles.
4. **Single-Occupant Power Users**: Focus on deep automation rules, AI predictive assistant queries, and memory vault personalization.

---

## 3. Daily Pilot Operational Cadence

| Time | Operation | Responsible Team | Actions |
|---|---|---|---|
| **08:00 UTC** | Health & Error Check | On-call Engineer | Review 5xx errors, latency anomalies, DLQ depth. |
| **12:00 UTC** | Pilot Engagement Monitor | Product Operations | Track daily active households, task completions, AI queries. |
| **16:00 UTC** | Support & Bug Triage | Engineering Support | Classify incoming user tickets (P0–P4) and assign owners. |
| **20:00 UTC** | Backup & Integrity Drill | Operations | Verify hourly snapshot generation and integrity checksums. |

---

## 4. Operational Telemetry & Health Signals

- **Application Performance**: p95 API response time target $< 50\text{ms}$; 5xx error rate $< 0.05\%$.
- **AI Cost per Active Household**: Target $< \$1.50\text{ / household / month}$.
- **Background Worker Latency**: Average job queue delay $< 500\text{ms}$.
- **Rate Limit Block Rate**: Monitor for false positives on high-activity household networks.
