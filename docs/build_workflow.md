# 🧱 UFFFS – Build Workflow (SFINCS)

> Reproducible workflow to build base SFINCS models using HydroMT and Snakemake.

---

## 🚀 Overview

This workflow automatically builds **base SFINCS model schematisations** that are later used in the event workflow.

It:

- ⚙️ Builds SFINCS models from configuration files
- 🏙️ Supports multiple cities and domains
- 🔁 Ensures reproducibility via Snakemake
- 🧱 Produces reusable base models (no rerun needed for each event)

---

## 🗂️ Workflow structure

```
workflows/
  Snakefile
  scripts/
    build_sfincs.py

config/
  cities.yml
  templates/
    sfincs/
      build_base.yml
```

---

## ⚙️ Configuration

Defined in:

```
config/cities.yml
```

Example:

```yaml
cities:
  Kampala:
    sfincs:
      kampala_sfincsmodel_01:
        group: default
        region: kampala_region
        build_config: config/templates/sfincs/build_base.yml
      kampala_sfincsmodel_01_lidar:
        group: lidar
        region: kampala_region
        build_config: config/templates/sfincs/build_base.yml
```

---

## 🧱 Base models

Models are written to:

```
outputs/{city}/sfincs_base/{sfmodel}
```

Example:

```
outputs/Kampala/sfincs_base/kampala_sfincsmodel_01
```

Each model contains:

- SFINCS configuration (`sfincs.inp`)
- grid definition (dep, mask, etc.)
- forcing placeholders
- GIS layers (DEM, mask, etc.)

These models are treated as:

✅ immutable (not modified during event runs)
✅ reusable across many events

---

## 🔁 Workflow steps

### 1. Prepare configuration

The workflow reads `cities.yml` and determines:

- which cities to build
- which SFINCS models per city
- which build template to use

---

### 2. Build SFINCS models

Script:

```
workflows/scripts/build_sfincs.py
```

This script:

- uses **HydroMT-SFINCS**
- applies the build template
- generates all required SFINCS input files

---

### 3. Write outputs

Each model is written to its own folder:

```
outputs/{city}/sfincs_base/{sfmodel}
```

---

## ▶️ Running

### Run all models

```bash
snakemake -c 1 -s workflows/Snakefile
```

---

### Dry run

```bash
snakemake -n -s workflows/Snakefile
```

---

## 📊 DAG visualisation

```bash
snakemake -s workflows/Snakefile --rulegraph | dot -Grankdir=LR -Tsvg > rulegraph_build.svg
```

---

## 📝 Logging

Logs per model:

```
logs/sfincs/{city}_{sfmodel}.log
```

---

## ✅ Key features

- ⚙️ Fully configuration-driven
- 🧱 Decoupled from event workflow
- 🔁 Reproducible model generation
- 🗺️ Automatic GIS data integration via HydroMT
- 📊 Suitable for multi-city scaling

---

## 🔗 Relation to event workflow

This workflow produces the **base models** used by:

👉 `docs/events_workflow.md`

The event workflow:
- reuses these base models
- adds forcing
- runs simulations
- postprocesses outputs

---

## 🚀 Future extensions

- 🧩 Multi-resolution domains
- 🌍 Additional cities and regions
- 🔄 Automated rebuilding based on config changes
- ☁️ Cloud-based execution

