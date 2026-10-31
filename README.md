# SENTRY

**Signals for Early Notification of Tension, Risk, and Yield**

SENTRY is an early-warning prototype that turns open news and conflict-event data into a country-level risk view. It trains a machine-learning model on weekly data for 15 countries, then presents the results in a citizen-friendly Streamlit dashboard with optional humanitarian-aid and disaster-alert layers.

> **Important:** SENTRY is a research prototype. Its scores are model-derived indicators, **not** predictions of specific events, calibrated probabilities, or a substitute for official travel or safety guidance.

---

## Table of contents

- [Features](#features)
- [How it works](#how-it-works)
- [Repository structure](#repository-structure)
- [Getting started](#getting-started)
- [Rebuilding the dataset](#rebuilding-the-dataset)
- [Dashboard guide](#dashboard-guide)
- [Model summary](#model-summary)
- [Results](#results)
- [Limitations](#limitations)
- [Data sources](#data-sources)
- [Tech stack](#tech-stack)
- [Authors and licence](#authors-and-licence)

---

## Features

- **Instability risk score (0–100):** the model's estimated chance that a country sees an unusual surge in protest or violent-event activity in the next 4 weeks, scaled to 100.
- **Hostility signal:** a 4-week average of the GDELT Goldstein hostility measure, shown as a separate map layer.
- **Interactive world map:** colour by risk or hostility, with hover details and a country ranking table.
- **Country explorer:** latest values for one country, with plain-language notes on how to read them.
- **Humanitarian aid layer (optional):** reported aid activities by recipient country and location, from the IATI datastore.
- **Disaster alerts layer (optional):** current alerts from GDACS.
- **Dark, calm visual theme** designed for non-expert users.

## How it works

```
GDELT (BigQuery) ─┐
                  ├─► weekly master table ─► 4-week features ─► XGBoost ─► risk score
ACLED (CSV)      ─┘                                                          │
                                                                             ▼
                                                      sentry_dashboard_data.csv
                                                                             │
IATI API ─┐                                                                  ▼
          ├─ fetched live, cached ───────────────────────────► Streamlit dashboard
GDACS RSS ┘
```

1. **Collect:** weekly news tone and hostility from GDELT; protest/riot and battle/violence counts from ACLED.
2. **Prepare:** merge by country (ISO-3) and Monday-start week, fill empty weeks with 0.
3. **Engineer features:** 4-week rolling means of past weeks only (no look-ahead).
4. **Label:** a country-week is positive if an unusual protest or battle surge occurs in the next 4 weeks.
5. **Train and score:** XGBoost classifier; the probability for the latest week becomes the risk score.
6. **Present:** the dashboard reads the exported CSV and fetches aid and disaster data on demand.

## Repository structure

```
Project-Sentry/
├── README.md
├── requirements.txt
├── requirements_citizen_ui.txt
├── sentry_citizen_ui_separate_aid_disaster_tabs.py   # Streamlit dashboard
├── sentry_dashboard_data (1).csv                     # Latest scores used by the dashboard
└── sentry_step1_data_collection.ipynb                # Data collection, modelling and export (Colab)
```

## Getting started

### Prerequisites

- Python 3.9 or newer
- Internet access (needed only for the optional aid and disaster layers)

### Install and run the dashboard

```bash
# 1. (Optional) create a virtual environment
python -m venv .venv
source .venv/bin/activate          # Windows: .venv\Scripts\activate

# 2. Install dependencies
pip install -r requirements.txt

# 3. Launch the app
streamlit run sentry_citizen_ui_separate_aid_disaster_tabs.py
```

Streamlit opens the dashboard at `http://localhost:8501`.

> **Note:** the app reads the file named `sentry_dashboard_data (1).csv` from the same folder. If you rename or replace the CSV, update the `uploaded = "..."` line near the top of the sidebar section in the script. A file-uploader line is included there as a comment if you prefer to upload a CSV in the browser.

### Expected CSV format

| Column | Description |
|---|---|
| `iso3` | ISO-3 country code (e.g. `IND`) |
| `week` | Date of the record |
| `risk_score` | Risk score on a 0–100 scale |
| `warning_level` | `WARNING` or `LOWER RISK` |
| `hostility_score` | 4-week average GDELT hostility signal |

The dashboard keeps the latest record per country.

## Rebuilding the dataset

The notebook `sentry_step1_data_collection.ipynb` is written for **Google Colab** and produces the dashboard CSV end to end. You will need:

- A **Google Cloud project** with BigQuery access (for the public `gdelt-bq.gdeltv2.events` table). Replace the `PROJECT` value in the notebook with your own project ID.
- **ACLED aggregated regional CSV exports**, placed in the Drive folder referenced in the notebook (`/content/drive/MyDrive/Sentrydata/`). ACLED data requires registration and is subject to its own terms of use.

Run the cells from top to bottom. Intermediate files are written to `data/`:

| File | Contents |
|---|---|
| `gdelt_weekly.csv` | Weekly news tone and hostility per country |
| `acled_weekly.csv` | Weekly protest and battle counts per country |
| `master_table.csv` | Merged weekly table (15 countries, 5,490 rows) |
| `model_table.csv` | Features and labels (5,400 rows, 15 columns) |
| `sentry_risk_scores.csv` | Latest-week risk scores |
| `sentry_hostility_scores.csv` | Latest 4-week hostility averages |
| `sentry_dashboard_data.csv` | Final merged file used by the dashboard |

## Dashboard guide

| Tab | What it shows |
|---|---|
| **Global overview** | Choropleth map (risk or hostility), summary cards, and a collapsible country ranking |
| **Explore a country** | Latest risk score, hostility signal and dataset status for the selected country |
| **Humanitarian aid** | IATI activity counts by country, mapped activity locations, and an activity table. Enable it in the sidebar |
| **Disaster alerts** | Current GDACS alerts with source links. Enable it in the sidebar |

The sidebar lets you choose what colours the map and switch the optional layers on or off. Optional layers are cached (aid: 60 minutes, disasters: 15 minutes).

## Model summary

| Item | Detail |
|---|---|
| Countries (15) | Afghanistan, Brazil, Burkina Faso, Ethiopia, Gabon, Haiti, India, Japan, Mali, Myanmar, Niger, Sudan, Syria, Ukraine, Yemen |
| Period | Weekly, 2018–2024 |
| Features | 4-week rolling means of protest count, battle count, news tone and hostility score (past weeks only) |
| Target | Unusual protest or battle surge (above the country's prior-52-week mean + 2 standard deviations, and at least 10 events) in any of the next 4 weeks |
| Model | `XGBClassifier`: 300 trees, max depth 4, learning rate 0.05, subsample 0.8, colsample 0.8 |
| Validation | Chronological split by week (about 80% train, 20% test): train 2018 to mid-2023, test mid-2023 to Dec 2024 |
| Warning rule | `WARNING` if predicted probability ≥ 0.20, otherwise `LOWER RISK` |

## Results

On the held-out test period (about 1,080 country-weeks, 22% positive rate):

| Metric | SENTRY | Reference |
|---|---|---|
| PR-AUC | 0.277 | 0.221 (constant base rate) |
| ROC-AUC | 0.569 | 0.500 (random ranking) |

| Threshold | Precision | Recall | F1 |
|---|---|---|---|
| 0.2 (used for WARNING) | 0.24 | 0.72 | 0.36 |
| 0.3 | 0.27 | 0.42 | 0.33 |
| 0.4 | 0.28 | 0.20 | 0.24 |
| 0.5 | 0.32 | 0.14 | 0.19 |

The model gives a modest improvement over the baseline. The 0.20 threshold favours catching more events (high recall) at the cost of many false alarms (low precision).

## Limitations

- **Modest predictive skill.** Scores should be read as relative signals, not forecasts.
- **Small country set.** Only 15 countries are covered, so the ranking is not a global one.
- **Event labels are proxy-based.** An "event" is defined statistically from ACLED counts, not from a verified list of crises.
- **Static snapshot.** The bundled CSV is a single week (2 December 2024). The dashboard does not update the risk model live.
- **Aid layer is limited.** It fetches 100 humanitarian activities from IATI and maps only the 15 project countries. Activity counts are not funding amounts and do not confirm delivery.
- **Hostility is not comparable across countries** in a strict sense and is a separate measure from the risk score.

## Data sources

- [GDELT 2.0 Events](https://www.gdeltproject.org/): news tone and Goldstein hostility (via Google BigQuery)
- [ACLED](https://acleddata.com/): protest, riot, battle and violence event counts
- [IATI Datastore](https://datastore.iati.cloud/): humanitarian aid activities
- [GDACS](https://www.gdacs.org/): global disaster alerts (RSS)

Please follow each provider's terms of use and attribution requirements.

## Tech stack

Python · pandas · XGBoost · scikit-learn · Google BigQuery · Streamlit · Plotly · requests · pycountry

## Authors and licence

- **Authors:** _add names here_
- **Licence:** _add a licence here (for example MIT) before publishing_
