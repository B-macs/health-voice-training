# SVD validation report

No licensed reference script was available (see PLAN.md), so this report validates the pipeline against real, professionally diagnosed voices from the Saarbruecken Voice Database (SVD) instead of byte-for-byte script parity. AVQI is the published Barsties v Latoszek formula reimplementation. ABI is a linear regression fit directly on REAL perceptual breathiness ratings from a separate database, VQD (see analysis/indices.py docstring and tests/fit_abi_vqd.py) -- SVD only provides diagnosis categories, not the breathiness ratings ABI predicts, so applying it here is a cross-dataset generalization check, not its primary validation (see tests/test_vqd_validation.py for that). ABI scores below are expected to be more COMPRESSED than on VQD, since SVD's dysphonia categories (e.g. Hyperfunktionelle = typically strained, not breathy) aren't primarily about breathiness -- correct ordering, not correct absolute cutoff-crossing, is what's checked here (see tests/test_discrimination.py).

Sample size: 41 (stratified across condition and sex, seed=123). Small-class caveat: Hypofunktionelle Dysphonie has only 16 complete recordings in the entire SVD. The AVQI cutoff below (German-validated, Barsties v Latoszek) is a real clinical cutoff; the ABI cutoff is the VQD model's own Youden-optimal threshold for detecting real breathiness, not validated for SVD's general dysphonia categories -- see analysis/abi_vqd_model.json.

## AVQI by condition (German cutoff: 2.7)

| condition | n | median | mean | min | max |
|---|---|---|---|---|---|
| healthy | 14 | 2.39 | 2.43 | 1.28 | 3.79 |
| Hyperfunktionelle Dysphonie | 14 | 3.64 | 3.59 | 1.99 | 5.39 |
| Hypofunktionelle Dysphonie | 12 | 3.27 | 3.03 | 1.98 | 3.67 |
| Internusschwäche | 1 | 4.32 | 4.32 | 4.32 | 4.32 |

AUC (healthy vs. any dysphonia) = 0.761; at cutoff 2.7: sensitivity = 0.73, specificity = 0.71 (n=40).

## ABI by condition (German cutoff: 2.0)

| condition | n | median | mean | min | max |
|---|---|---|---|---|---|
| healthy | 14 | 0.00 | 0.21 | 0.00 | 1.77 |
| Hyperfunktionelle Dysphonie | 14 | 0.85 | 1.37 | 0.00 | 4.30 |
| Hypofunktionelle Dysphonie | 12 | 0.57 | 0.79 | 0.00 | 2.37 |
| Internusschwäche | 1 | 4.04 | 4.04 | 4.04 | 4.04 |

AUC (healthy vs. any dysphonia) = 0.747; at cutoff 2.0: sensitivity = 0.23, specificity = 1.00 (n=40).
