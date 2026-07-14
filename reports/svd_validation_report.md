# SVD discrimination report (archived)

> **Archive note (2026-07-14):** This historical SVD output predates the
> versioned capture protocol and must not be read as reference-script parity
> or as validation of Voxplot's 2.70 AVQI personal-trend boundary as a
> German clinical cutoff. The German equalised-protocol paper reports 1.85.
> The current policy is in `docs/voice_quality_measurement_policy.md`.

No licensed reference script was available (see PLAN.md), so this report checks
whether the pipeline ordered real, professionally diagnosed Saarbruecken Voice
Database (SVD) recordings in the expected direction. AVQI is a published-formula
reimplementation. ABI is a VQD-trained breathiness estimate; SVD has diagnosis
categories, not the perceptual breathiness ratings it predicts. This is thus a
cross-dataset regression check, not primary validation or proof of a clinical
threshold.

Sample size: 41 (stratified across condition and sex, seed=123). Small-class
caveat: Hypofunktionelle Dysphonie has only 16 complete recordings in the
entire SVD. The historical values below remain for reproducibility only.

## AVQI by condition (historical app boundary: 2.7)

| condition | n | median | mean | min | max |
|---|---|---|---|---|---|
| healthy | 14 | 2.39 | 2.43 | 1.28 | 3.79 |
| Hyperfunktionelle Dysphonie | 14 | 3.64 | 3.59 | 1.99 | 5.39 |
| Hypofunktionelle Dysphonie | 12 | 3.27 | 3.03 | 1.98 | 3.67 |
| Internusschwäche | 1 | 4.32 | 4.32 | 4.32 | 4.32 |

AUC (healthy vs. any dysphonia) = 0.761; at cutoff 2.7: sensitivity = 0.73, specificity = 0.71 (n=40).

## ABI by condition (historical pre-Lasso boundary: 2.0)

| condition | n | median | mean | min | max |
|---|---|---|---|---|---|
| healthy | 14 | 0.00 | 0.21 | 0.00 | 1.77 |
| Hyperfunktionelle Dysphonie | 14 | 0.85 | 1.37 | 0.00 | 4.30 |
| Hypofunktionelle Dysphonie | 12 | 0.57 | 0.79 | 0.00 | 2.37 |
| Internusschwäche | 1 | 4.04 | 4.04 | 4.04 | 4.04 |

AUC (healthy vs. any dysphonia) = 0.747; at cutoff 2.0: sensitivity = 0.23, specificity = 1.00 (n=40).
