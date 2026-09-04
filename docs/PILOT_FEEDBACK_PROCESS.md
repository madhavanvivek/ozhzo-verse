# OZHZO VERSE — PILOT FEEDBACK & TRIAGE PROCESS

---

## 1. Feedback Channels

Pilot households can provide feedback through:
- In-App Quick Feedback widget in the bottom navigation and settings.
- Direct Pilot Community Channel (weekly asynchronous check-in).
- Structured End-of-Week 3-question survey.

---

## 2. Triage & Categorization Matrix

Every piece of user feedback is classified into one of 6 structural categories before consideration:

```
[ Incoming Pilot Feedback ]
               │
               ├─► [ 1. Genuine Bug / Defect ] ──► (Create Incident P1/P2/P3)
               │
               ├─► [ 2. Usability / Friction ] ──► (Simplify Copy / Improve Flow)
               │
               ├─► [ 3. Onboarding Confusion ] ──► (Clarify First-10-Minute UX)
               │
               ├─► [ 4. Missing Capability ]  ──► (Score Against Prioritization Matrix)
               │
               ├─► [ 5. Edge Case ]           ──► (Assess Household Breadth)
               │
               └─► [ 6. Isolated Preference ] ──► (Archive for Future Review)
```

---

## 3. Prioritization Scoring Formula

Potential post-pilot improvements are scored using:

$$\text{Priority Score} = \frac{\text{User Value} \times \text{Retention Impact} \times \text{Household Breadth}}{\text{Implementation Cost} \times \text{Complexity Risk}}$$

Features with low household breadth or high speculative complexity are rejected to preserve core architectural stability.
