# VQD validation report

The authoritative ABI validation for this project: 296 recordings from the Perceptual Voice Qualities Database (VQD), each independently rated by 3-4 expert clinicians (2 trials each) on GRBAS and CAPE-V, including Breathiness (ICC .844 interrater / .884 intrarater -- see 'Voice Samples Direct Download/Introduction, Methods and Reliability/database overview v2.pdf'). Unlike SVD, this provides the actual continuous perceptual construct ABI is supposed to predict, not a diagnosis-category proxy. See analysis/indices.py module docstring for the full three-stage investigation this resolved.

NOTE: `vqd_fitted` below is in-sample (the deployed model was fit on all 296 of these recordings) -- the honest held-out estimate is the 5-fold CV figure reported by tests/fit_abi_vqd.py.

Sample size: 296

## Correlation with real perceptual ratings

| model | vs GRBAS-Breathiness (r) | vs CAPE-V-Breathiness (r) |
|---|---|---|
| published Barsties formula | -0.154 | -0.187 |
| VQD-fitted (deployed, in-sample) | 0.838 | 0.853 |

5-fold cross-validated (honest, held-out) Pearson r = 0.814 (RMSE 0.451 on the 0-3 GRBAS-B scale).

## ABI (deployed model) by GRBAS-Breathiness category

| category | n | median | mean | min | max |
|---|---|---|---|---|---|
| Normal | 174 | 1.10 | 1.21 | 0.00 | 4.49 |
| Mild | 78 | 2.57 | 2.75 | 0.17 | 6.41 |
| Moderate | 28 | 6.07 | 5.87 | 3.50 | 8.95 |
| Severe | 16 | 7.03 | 6.71 | 2.03 | 9.51 |

AUC (any breathiness present, GRBAS-B > 0.5) = 0.894; at cutoff 2.0 (0-10 scale): sensitivity = 0.82, specificity = 0.80 (n=296).
