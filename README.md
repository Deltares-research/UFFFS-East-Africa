# 🌍 UFFFS – Urban Flood Forecasting Framework

> Reproducible, scalable workflow for building and running urban flood models using **Snakemake + HydroMT + SFINCS**

---

## 🚀 Overview

UFFFS provides a **fully configuration-driven workflow** for:

- 🧱 Building base SFINCS model schematisations
- 🌧️ Running flood events with different forcing scenarios
- 🗺️ Postprocessing and merging floodmaps
- 🧩 Comparing model configurations (e.g. baseline vs lidar)

The framework is designed for:

- reproducibility ✅  
- scalability across cities ✅  
- efficient reuse of models ✅  

---

## 🧭 Workflows

UFFFS consists of two main workflows:

---

### 🧱 Build workflow

Builds reusable **base SFINCS models** using HydroMT.

- Reads configuration from `config/cities.yml`
- Generates model schematisations
- Writes outputs to:

```
outputs/{city}/{sfmodel}/sfincs_base/
```

📖 See:
👉 `docs/build_workflow.md`

---

### 🌧️ Event workflow

Runs **event simulations** on top of base models.

- Updates forcing (ERA5 / synthetic)
- Runs SFINCS
- Postprocesses floodmaps
- Merges results **per model group**

Outputs:

```
outputs/{city}/events/{event}/
  {city}_{event}_{group}_floodmap.tif
```

📖 See:
👉 `docs/events_workflow.md`

---

## 🗂️ Repository structure

```
├── config/
│   ├── cities.yml                 # Model definitions (incl. groups)
│   ├── events.yml                 # Event configuration
│   └── templates/
│       └── sfincs/
│           └── build_base.yml
│
├── workflows/
│   ├── Snakefile                  # Build workflow
│   ├── Snakefile_events           # Event workflow
│   └── scripts/
│       ├── build_sfincs.py
│       ├── update_sfincs_forcing.py
│       ├── postprocess_sfincs.py
│       └── merge_floodmaps.py
│
├── docs/
│   ├── build_workflow.md
│   └── events_workflow.md
│
├── outputs/                       # Generated models and results
├── logs/                          # Log files
```

---

## ⚙️ Configuration

### Base models

Defined in:

```
config/cities.yml
```

Includes:
- model definitions
- grouping (e.g. baseline / lidar)
- build templates

---

### Events

Defined in:

```
config/events.yml
```

Includes:
- event timing
- forcing type
- model or group selection

---

## ▶️ Running

### Build base models

```
snakemake -c 4 -s workflows/Snakefile
```

---

### Run events

```
snakemake -c 4 -s workflows/Snakefile_events
```

---

### Dry run

```
snakemake -n -p -s workflows/Snakefile_events
```

---

## 📊 DAG visualisation

Build workflow:

```
snakemake -s workflows/Snakefile --rulegraph | dot -Grankdir=LR -Tsvg > rulegraph_build.svg
```

Event workflow:

```
snakemake -s workflows/Snakefile_events --rulegraph | dot -Grankdir=LR -Tsvg > rulegraph_events.svg
```

---

## 📝 Logging

Logs are written per step:

```
logs/sfincs/       # build workflow
logs/events/       # event workflow
```

---

## 🧱 Architecture principle

The framework separates:

| Component | Role |
|----------|------|
| `sfincs_base` | immutable base models |
| `events`      | event-specific runs |
| scripts       | execution logic |
| Snakefiles    | workflow orchestration |

This ensures:

- ✅ no duplication of large model data (hardlinks used)
- ✅ efficient scaling
- ✅ reproducibility

---

## 🧪 Environment

### Pixi

Install:
```
pixi install
```

Run:
```
pixi run run
```

---

### Conda

```
conda env create -f environment.yml
conda activate ufffs
```

---

## 🚀 Future extensions

- 🌍 Multi-city scaling
- 📊 Ensemble simulations
- 🔄 Automated rebuild triggers
- ☁️ Cloud execution (AWS / batch)
- 📉 Model comparison (e.g. lidar vs baseline)

---
