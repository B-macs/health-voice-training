# VQD validation report — archived pre-Lasso snapshot

> **Historical report, not the current deployment result.** This file was
> generated before the production Lasso refit. Its 0.814 / 0.894 / 2.0
> figures and category table describe the former OLS model. The current
> runtime model is `analysis/abi_vqd_model.json`: Lasso, threshold 2.10,
> five-fold CV Pearson r 0.809, RMSE 0.455, AUC 0.888, sensitivity 0.81, and
> specificity 0.82. Run `python tests/generate_vqd_report.py` with the cached
> VQD results to regenerate this report for the current model; the generator
> now reads the model's threshold rather than hard-coding 2.0.

The VQD source data are the authoritative perceptual breathiness dataset for
this project: 296 recordings independently rated by 3-4 expert clinicians (2
trials each) on GRBAS and CAPE-V, including Breathiness (ICC .844 interrater /
.884 intrarater). Unlike SVD, this provides the actual continuous perceptual
construct the custom Voxplot breathiness estimate targets, not a
diagnosis-category proxy. See `analysis/indices.py` for the four-stage
investigation.

NOTE: `vqd_fitted` below is in-sample for the archived OLS model. The current
model's out-of-fold metrics are held in its JSON artifact until this report is
regenerated from `tests/vqd_results.csv`.

Sample size: 296

## Correlation with real perceptual ratings

| model | vs GRBAS-Breathiness (r) | vs CAPE-V-Breathiness (r) |
|---|---|---|
| published Barsties formula | -0.154 | -0.187 |
| VQD-fitted (deployed, in-sample) | 0.838 | 0.853 |

5-fold cross-validated (honest, held-out) Pearson r = 0.814 (RMSE 0.451 on the 0-3 GRBAS-B scale).

## Archived OLS model by GRBAS-Breathiness category

| category | n | median | mean | min | max |
|---|---|---|---|---|---|
| Normal | 174 | 1.10 | 1.21 | 0.00 | 4.49 |
| Mild | 78 | 2.57 | 2.75 | 0.17 | 6.41 |
| Moderate | 28 | 6.07 | 5.87 | 3.50 | 8.95 |
| Severe | 16 | 7.03 | 6.71 | 2.03 | 9.51 |

AUC (any breathiness present, GRBAS-B > 0.5) = 0.894; at cutoff 2.0 (0-10 scale): sensitivity = 0.82, specificity = 0.80 (n=296).
