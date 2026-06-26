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
snakemake -c 1 -s workflows/Snakefile
```

---

### Run events

```
snakemake -c 1 -s workflows/Snakefile_events
```

---

### Dry run

```
snakemake -n -s workflows/Snakefile_events
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
## 💾 Data management (DVC + MinIO)

This project uses **DVC (Data Version Control)** to manage large datasets and model inputs/outputs.

- Git → code and configuration (Snakemake, YAML, scripts)
- DVC → large data (models, forcing, outputs)
- MinIO (S3) → remote storage

---

## 🔧 First-time setup

### 1. Install DVC

```bash
pip install dvc[s3]
```

### 2. Configure MinIO credentials

Each user must set their own credentials locally:

```bash
dvc remote modify miniostorage --local access_key_id YOUR_ACCESS_KEY
dvc remote modify miniostorage --local secret_access_key YOUR_SECRET_KEY
```

### 3. Pull data

```bash
dvc pull
```

---

## 🔄 Typical workflow

### Pull data

```bash
dvc pull
```

### Track new data

```bash
dvc add <file_or_folder>
git add <file>.dvc .gitignore
git commit -m "track data"
```

### Push data

```bash
dvc push
```

---

## ⚙️ Remote configuration

Shared (in `.dvc/config`):

```ini
['remote "miniostorage"']
    url = s3://fews-dca
    endpointurl = https://s3.deltares.nl
```

Private (in `.dvc/config.local`, NOT committed):

```ini
['remote "miniostorage"']
    access_key_id = XXX
    secret_access_key = XXX
```

---

## 🔐 Security notes

- Never commit access keys
- `.dvc/config.local` is ignored by Git
- Each user has their own credentials

---


---

##  Notes

- HydroMT might not be able to run in parallel, so better to use 1 core: '-c 1'

---
