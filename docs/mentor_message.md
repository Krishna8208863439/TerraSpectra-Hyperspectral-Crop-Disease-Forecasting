# Mentor Scope Confirmation & Check-In Message (Day 1 — Block 1)

**Status:** Drafted & Ready to Send (Mon 16 Nov)  
**Rule:** If no reply is received by Tuesday morning, proceed with the primary open-access leaf/plant spectral dataset selected in `docs/dataset_note.md`.

---

## Message Template

Subject: Day 1 Scope Confirmation, Dataset Check & Progress Update Cadence

Hi [Mentor Name],

I am kicking off Day 1 setup for the spectral crop stress/disease project today and want to confirm three quick items so we have zero blockers for the week:

1. **Project Scope Confirmation:**
   - **Part A — Detection Baseline:** Classify healthy vs. stressed/diseased leaf/canopy samples from spectral reflectance signatures using tabular ML baselines (`scikit-learn` Logistic Regression / Random Forest and `XGBoost`), evaluated with leak-free group splits.
   - **Part B — Simple Temporal Forecast:** Model spectral/stress index progression (e.g., NDVI / Red-Edge NDRE trajectory or class transition risk) across consecutive measurement dates to forecast short-horizon plant stress progression.
   - Please let me know if you want any adjustments to this two-part scope.

2. **Dataset Availability:**
   - Do you have an internal or preferred dataset you would like me to use?
   - If not, I am evaluating open-access spectral datasets across Kaggle, Zenodo, Mendeley Data, and IEEE DataPort following the agreed fallback order (1: leaf-level spectral crop disease/stress CSV, 2: Indian Pines / Salinas pipeline benchmark, 3: synthetic controlled-stress spectra) and will lock in the best licensed option today.

3. **Progress Update Cadence:**
   - How would you prefer to receive progress updates (e.g., brief end-of-day summary in Slack/email with commit links, or a mid-week review)?

Best regards,  
[Your Name]

---

## Scope & Decision Log

| Item | Confirmed Decision | Notes |
| --- | --- | --- |
| Primary Goal | Detection baseline + simple temporal forecast | Two-stage modeling plan |
| Leak-Free Split Requirement | Group by plant/pot and date (`Plant_ID`, `Pot_Number`, `date`) | Carried forward to Day 2 & Day 5 |
| Fallback Cutoff | Tuesday morning | Auto-proceed with documented Zenodo dataset if no reply |
