# 🌧️ UFFFS – Event Workflow (SFINCS)

> Run hydrodynamic flood simulations for defined events using existing base SFINCS models, and postprocess + merge results.

---

## 🚀 Overview

This workflow builds on the **base SFINCS models** and performs:

1. ⚙️ Update model forcing (HydroMT-SFINCS)
2. 🌊 Run SFINCS simulations
3. 🗺️ Postprocess floodmaps (downscaling)
4. 🧩 Merge floodmaps across models **per group**

---

## 🗂️ Workflow structure

```
workflows/
  Snakefile_events
  scripts/
    update_sfincs_forcing.py
    postprocess_sfincs.py
    combine_floodmaps.py
```

---

## ⚙️ Configuration

Defined in:

```
config/events.yml
```
In the config you can define an event with several config options:
- start: start date
- end: end date of simulation
- models: either a list of models or 'all'
- group (optional): an optional group element in case you have a separate group of base models (e.g. with different DEM)
- forcing:
  - type: either 'catalog' to read an entry from the data catalog or 'synthetic_constant' to generate a synthetic event
  - precip: the catalog key (only necessary for type:catalog)
  - precipitation_mm_per_hr: only necessary for type: synthetic_constant
- postprocess:
  - hmin: Minimum water depth for generation of floodmaps

Example:

```yaml
global:
  data_libs: "deltares_data"
  sfincs_exe: "path/to/sfincs.exe"

cities:
  Kampala:
    events:
      era5_may2024:
        start: "20200501 000000"
        end: "20200503 000000"
        models: 
          - kampala_sfincsmodel_01
        forcing:
          type: catalog
          precip: "era5_hourly"
        postprocess:
          hmin: 0.05
      synthetic_100mm_24h:
        start: "20240601 000000"
        end: "20240601 030000"
        models: all
        forcing:
          type: synthetic_constant
          precipitation_mm_per_hr: 4.1666667
        postprocess:
          hmin: 0.05
```

---

## 🧱 Model groups

Model groups are defined in:

```
config/cities.yaml
```

Example:

```yaml
kampala_sfincsmodel_01:
  group: default
```

Merged floodmaps are generated per group.

---

## 📂 Outputs

Per model:
```
outputs/{city}/events/{event}/{sfmodel}/floodmap.tif
```

Per group:
```
outputs/{city}/events/{event}/{city}_{event}_{group}_floodmap.tif
```

---

## ▶️ Running

Run workflow:
```
snakemake -c 4 -s workflows/Snakefile_events
```

Dry run:
```
snakemake -n -p -s workflows/Snakefile_events
```

---

## 📝 Logging

```
logs/events/
```

---

## ✅ Key features

- Config-driven
- Supports model groups
- Reuses base models (no duplication): duplicate files are stored with hardlinks to save space
- Supports real and synthetic events
- Merges outputs per group

