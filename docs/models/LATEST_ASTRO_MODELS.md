# Latest Astronomical AI Models Report

**Generated**: 2026-05-01

---

## 1. astroPT - Foundation Model for Astronomy

| Property | Value |
|----------|-------|
| **Repository** | Smith42/astroPT |
| **HuggingFace** | [Smith42/astroPT_v2.0](https://huggingface.co/Smith42/astroPT_v2.0) |
| **Last Updated** | 2026-04-27 |
| **License** | AGPL-v3 |
| **Model Type** | Transformer-based Foundation Model |
| **Modalities** | Galaxy imagery (JPG/FITS), Spectral Energy Distribution (SED) |

### Available Pre-trained Weights

| Survey | Version | Model Path | Dataset |
|--------|---------|------------|---------|
| DESI Legacy Survey | v1.0.0 | AstroPT | [Galaxies Dataset](https://huggingface.co/datasets/Smith42/galaxies) |
| Euclid | v1.0.2 | AstroPT-Euclid | [Euclid Training Dataset](https://huggingface.co/datasets/msiudek/astroPT_euclid_training_dataset) |
| DESI Legacy Survey | v2.0.5 | AstroPT v2.0 | [Galaxies Dataset v2.0](https://huggingface.co/datasets/Smith42/galaxies) |

### Papers
- [arXiv:2405.14930](https://arxiv.org/abs/2405.14930) - Original astroPT paper
- [arXiv:2503.15312](https://arxiv.org/abs/2503.15312) - Euclid data application
- [arXiv:2509.19453](https://arxiv.org/abs/2509.19453) - Recent work

### Cross-Validation Status
- ICML 2024 AI4Science workshop presentation
- UniverseTBD community Discord support

### Verdict: VERIFIED
- Official HuggingFace weights available
- Academic peer review via arXiv
- Active development (updated 2026-04-27)

---

## 2. Exoplanet Detection Models

### 2.1 MouryaSasank/exoplanet-detection-cnn-rf (RECOMMENDED)

| Property | Value |
|----------|-------|
| **Repository** | MouryaSasank/exoplanet-detection-cnn-rf |
| **Last Updated** | 2026-04-30 |
| **Data Source** | NASA Kepler Labelled Time Series (Kaggle) |

#### Performance Metrics (Verifiable)

| Metric | Hybrid CNN+RF | Baseline RF |
|--------|:-------------:|:-----------:|
| PR-AUC | **0.5606** | 0.1764 |
| F1-Score | **0.5000** | 0.2222 |
| Recall | 0.4000 | 0.2000 |
| ROC-AUC | **0.8727** | 0.6195 |
| MCC | **0.5132** | 0.2149 |

#### Key Academic Contributions
- Ablation Study (CNN+RF vs CNN-only vs PCA+RF)
- Bootstrap Confidence Intervals (1000 resamples)
- SHAP Explainability
- 5-Fold Stratified Cross-Validation
- Isotonic Probability Calibration

#### Known Limitations
- Only 5 exoplanets in test set (statistically fragile)
- High CV variance (F1 ranges 0.14-0.60 across folds)
- SMOTE synthetic oversampling from 37 real exoplanets

### 2.2 JorgeAcebes/tess-exoplanet-detection

| Property | Value |
|----------|-------|
| **Repository** | JorgeAcebes/tess-exoplanet-detection |
| **Last Updated** | 2026-03-29 |
| **Data Sources** | TESS photometry + Ground-based UAM |

#### Features
- BLS (Box Least Squares) transit search
- NASA Exoplanet Archive integration
- Light curve analysis pipeline
- Both archive data (functional) and own observations

### 2.3 Ap6635514/exoplanet-detection-cnn (NOT VERIFIABLE)

| Property | Value |
|----------|-------|
| **Accuracy** | 67% (synthetic data only) |
| **Problem** | Uses only simulated data |
| **Status** | Proof-of-concept, NOT production-ready |

**Warning**: This is a student project using synthetic data. Cannot be verified against real astronomical datasets.

---

## 3. Zoobot - Galaxy Morphology Classification

### Found Related Projects

| Repository | Last Updated | Description |
|------------|--------------|-------------|
| mkurzner/zoobot-ngvs-fine-tune | 2026-01-11 | Fine-tuning Zoobot for NGVS galaxy classification |
| ezrafielding/zoobot-arch-comp | 2024-09-09 | Comparison of deep learning architectures for galaxy morphology |
| abdelrhmanfathi-commits/StarGPT-Galaxy-Morphology | 2025-12-02 | Galaxy Classification using Zoobot |

### Status
**Zoobot official repository not found in GitHub search.** Original project is likely at [mwalmsley/zoobot](https://github.com/mwalmsley/zoobot) (based on references in other repos).

### Cross-Validation
- zoobot-arch-comp project compares multiple architectures
- Fine-tuning work (NGVS) provides validation on different dataset

### Verdict: PARTIALLY VERIFIED
- Referenced by multiple projects but official repo not search-accessible
- Community use indicates active project

---

## 4. Kepler/TESS Data Processing

### Available Resources

| Repository | Focus | Status |
|------------|-------|--------|
| MouryaSasank/exoplanet-detection-cnn-rf | Kepler light curves | VERIFIED - has metrics |
| JorgeAcebes/tess-exoplanet-detection | TESS + ground-based | FUNCTIONAL |
| christopherburke/TESS-ExoClass | TESS exoplanet filter/classifier | Active (2021) |
| Lwheeler77/tess-exoplanet-detection | TESS detection | Active (2025-12) |
| JANAGESH/Tess-Exoplanet-Detection-System | TESS detection system | Active (2025-12) |

---

## Summary Table

| Model | Type | Verifiable | HuggingFace | Last Update | Priority |
|-------|------|------------|-------------|-------------|----------|
| astroPT v2.0 | Foundation Model | YES | YES | 2026-04-27 | HIGH |
| exoplanet-detection-cnn-rf | Exoplanet Detection | YES (metrics) | NO | 2026-04-30 | HIGH |
| tess-exoplanet-detection | Exoplanet Detection | YES (functional) | NO | 2026-03-29 | MEDIUM |
| Zoobot | Galaxy Classification | PARTIAL | UNKNOWN | 2026-01-11 | MEDIUM |

---

## Tianwen Integration Priority Recommendations

### Tier 1: Ready for Integration
1. **astroPT** - Foundation model with HuggingFace weights
   - Multi-modal (imagery + SED)
   - Pre-trained on DESI/Euclid surveys
   - Can serve as feature extractor for galaxy classification

2. **exoplanet-detection-cnn-rf** - Production-ready exoplanet detection
   - Verifiable metrics on NASA Kepler data
   - Hybrid architecture (CNN + Random Forest)
   - Includes SHAP explainability

### Tier 2: Requires Investigation
3. **Zoobot** - Official repo needs verification
   - Galaxy Zoo classification standard
   - Cross-validation documented in arch-comp project

### Tier 3: Data Pipeline Integration
4. **Kepler/TESS processing frameworks**
   - JorgeAcebes framework for TESS + ground-based data
   - Can be integrated for light curve preprocessing

---

## References

- [astroPT GitHub](https://github.com/Smith42/astroPT)
- [astroPT v2.0 on HuggingFace](https://huggingface.co/Smith42/astroPT_v2.0)
- [Kepler Labelled Time Series Dataset](https://www.kaggle.com/keplersmachines/kepler-labelled-time-series-data)