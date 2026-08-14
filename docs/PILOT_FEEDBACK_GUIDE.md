# Ozhzo Verse — MVP Pilot Feedback & Evaluation Guide

**Document**: Pilot Feedback Guide  
**Target**: Household Pilot Coordinator, Product Lead  
**Cohort**: 5–10 Multi-Member Households (2–4 Week Duration)  

---

## 1. Objective of the MVP Pilot
The goal of the pilot is **qualitative and operational validation** of the Digital Home OS value proposition:
> **"Does Ozhzo Verse remember my home and help my family run it without unnecessary friction?"**

---

## 2. In-App Feedback Touchpoint
Users can submit real-time impressions directly from the app via:
- Web: Header `Feedback` button.
- Mobile: Settings ➔ Send Feedback.
- API: `POST /api/v1/homes/{home_id}/feedback`.

Fields Captured:
- `category`: `FEEDBACK`, `BUG`, `FEATURE_REQUEST`
- `message`: Free-text user feedback (max 2000 chars)
- `rating`: 1 to 5 stars (optional)
- `app_version`: `0.1.0-pilot.1`

---

## 3. The 10 Structured Pilot Household Interview Questions

Conduct these interviews with participating family members at the end of Week 1 and Week 4:

```
┌─────────────────────────────────────────────────────────────────────────────┐
│                    10 STRUCTURED PILOT INTERVIEW QUESTIONS                  │
├─────────────────────────────────────────────────────────────────────────────┤
│  1. What was the very first thing you used Ozhzo for in your home?          │
│                                                                             │
│  2. Did you ever search for an item or tool whose location you forgot?      │
│                                                                             │
│  3. Did Ozhzo's Home Memory successfully help you find where it was kept?   │
│                                                                             │
│  4. Did another family member in your home add, move, or complete anything? │
│                                                                             │
│  5. Did your household use the shared Purchase List during grocery shopping?│
│                                                                             │
│  6. Did Chores & Tasks actually reduce family coordination effort or texts? │
│                                                                             │
│  7. Did Bills & Reminders help prevent a late utility fee or forgotten bill?│
│                                                                             │
│  8. Did the "Today" agenda view become your daily morning check-in?         │
│                                                                             │
│  9. What part of the app felt unnecessary, confusing, or clunky?            │
│                                                                             │
│ 10. What did you expect Ozhzo to do for your home that it currently cannot? │
└─────────────────────────────────────────────────────────────────────────────┘
```

---

## 4. Evaluation Rubric & Decision Signals

| Metric / Signal | Strong Positive (Green) | Acceptable (Yellow) | Problematic (Red) |
|---|---|---|---|
| **Home Memory Value** | $\ge 80\%$ found stored item via search | $50–79\%$ found item | $< 50\%$ found search useful |
| **Multi-Member Collaboration** | $\ge 70\%$ of homes have $\ge 2$ active members | $40–69\%$ multi-member | $< 40\%$ (single user only) |
| **7-Day Retention** | $\ge 75\%$ weekly active homes | $50–74\%$ active | $< 50\%$ churn |
| **Purchase $\rightarrow$ Inventory Restock** | Checked shopping items restocked pantry | Used shopping list only | Ignored purchase list |
| **Task & Chore Completion** | $\ge 3$ chores completed per week | $1–2$ chores completed | $0$ chores completed |
