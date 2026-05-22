# 🌍 UFFFS – Urban Flood Forecasting Framework Setup

> Reproducible, scalable workflow for building hydrological and hydrodynamic models using **Snakemake + HydroMT**

---

## 🚀 Overview

This repository provides a **configuration-driven workflow** for generating SFINCS (and optionally Wflow) models.

The workflow:

- ⚙️ Builds models from YAML configurations
- 🏙️ Supports multiple cities and domains
- 🔁 Automatically reruns when inputs/config/scripts change
- 📊 Provides DAG visualisation
- 📝 Generates per-model logs

---

## 🗂️ Repository structure

```

├── config/
│   ├── cities.yaml                  # Main configuration
│   └── templates/
│       └── sfincs/
│           └── build_base.yml       # Base HydroMT template
│
├── workflows/
│   ├── Snakefile                   # Snakemake workflow
│   └── scripts/
│       └── build_sfincs.py         # Model build logic
│
├── outputs/                        # Generated models
├── logs/                           # Log files
```
---

## Configuration

Defined in:
config/cities.yaml

Example:
```
cities:
  Kampala:
    sfincs:
      kampala_sfincsmodel_01:
        region: cities/Kampala/regions/domain.geojson
        build_config: config/templates/sfincs/build_base.yml
        build_overrides: config/overrides/kampala.yml
        model_dir: outputs/Kampala/sfincs/kampala_sfincsmodel_01/base
```
---

## Running

Run all:
```
snakemake -c 4 -s workflows/Snakefile
```
Dry run:
```
snakemake -n -p -s workflows/Snakefile
```
---

## DAG
```
snakemake -s workflows/Snakefile --rulegraph | dot -Grankdir=LR -Tsvg > rulegraph.svg
```
---

## Logging

Logs are written per model:
logs/sfincs/{city}_{sfmodel}.log

---

## Environment 

### Pixi

Install environment:
```
pixi install
```
Run workflow:
```
pixi run run
```
### Conda
```
conda env create -f environment.yml
conda activate ufffs
```