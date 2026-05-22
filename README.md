# UFFFS – Urban Flood Forecasting Framework Setup

This repository contains a reproducible workflow for building hydrological and hydrodynamic models (SFINCS, and optionally Wflow) using Snakemake and HydroMT.

---

## Overview

This framework:
- Builds SFINCS models from YAML templates
- Supports multiple cities and domains
- Uses Snakemake for orchestration
- Tracks dependencies for reproducibility
- Provides per-model logging and DAG visualisation

---

## Repository structure

.
├── config/              # Configuration files
├── workflows/           # Snakemake workflow + scripts
├── outputs/             # Generated models
├── logs/                # Log files

---

## Configuration

Defined in:
config/cities.yaml

Example:

cities:
  Kampala:
    sfincs:
      model_01:
        region: path/to/region.geojson
        build_config: config/templates/sfincs/build_base.yml

---

## Running

Run all:
snakemake -c 1 -s workflows/Snakefile

Dry run:
snakemake -n -p -s workflows/Snakefile

---

## DAG

snakemake -s workflows/Snakefile --rulegraph | dot -Grankdir=LR -Tsvg > rulegraph.svg

---

## Logging

Logs are written per model:
logs/sfincs/{city}_{sfmodel}.log

---

## Requirements

conda install -c conda-forge snakemake graphviz hydromt hydromt_sfincs

---

## Notes

- Snakemake ensures reproducibility by tracking inputs, configs, and scripts
- Python scripts handle model generation
- YAML files define configuration
