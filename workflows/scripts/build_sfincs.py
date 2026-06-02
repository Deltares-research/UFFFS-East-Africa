from pathlib import Path
import yaml
import copy
import logging
import sys
import os

from hydromt_sfincs import SfincsModel


def main(snakemake):
    # -----------------------------
    # 0. Setup logging
    # -----------------------------
    log_file = None
    if hasattr(snakemake, "log") and len(snakemake.log) > 0:
        log_file = snakemake.log[0]

    # configure logging (file + console)
    handlers = [logging.StreamHandler(sys.stdout)]
    if log_file:
        Path(log_file).parent.mkdir(parents=True, exist_ok=True)
        handlers.append(logging.FileHandler(log_file))

    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s [%(levelname)s] %(message)s",
        handlers=handlers,
    )

    logging.info("=== Starting SFINCS build ===")

    # -----------------------------
    # 1. Get Snakemake variables
    # -----------------------------
    city = snakemake.wildcards.city
    sfmodel = snakemake.wildcards.sfmodel
    config = snakemake.config

    sf_cfg = config["cities"][city]["sfincs"][sfmodel]

    region_path = sf_cfg["region"]
    build_base_path = sf_cfg["build_config"]
    build_overrides_path = sf_cfg.get("build_overrides")

    model_root = Path(sf_cfg.get("model_dir", f"outputs/{city}/sfincs/{sfmodel}/base"))
    model_root.mkdir(parents=True, exist_ok=True)

    logging.info(f"City: {city}")
    logging.info(f"Model: {sfmodel}")
    logging.info(f"Region: {region_path}")
    logging.info(f"Model root: {model_root}")
    logging.info(f"Base config: {build_base_path}")
    logging.info(f"Overrides config: {build_overrides_path}")

    # -----------------------------
    # 2. Load YAML files
    # -----------------------------
    def load_yaml(path):
        if not path:
            return {}
        with open(path) as f:
            return yaml.safe_load(f) or {}

    base = load_yaml(build_base_path)
    overrides = load_yaml(build_overrides_path)

    logging.debug("Loaded YAML configurations")

    # -----------------------------
    # 3. Merge base + overrides
    # -----------------------------
    def merge(a, b):
        out = copy.deepcopy(a)
        for k, v in (b or {}).items():
            if k in out and isinstance(out[k], dict) and isinstance(v, dict):
                out[k] = merge(out[k], v)
            else:
                out[k] = copy.deepcopy(v)
        return out

    cfg = merge(base, overrides)

    logging.debug("Merged base and override configs")

    # -----------------------------
    # 4. Inject region
    # -----------------------------
    for step in cfg["steps"]:
        if "grid.create_from_region" in step:
            step["grid.create_from_region"]["region"] = {"geom": region_path}
        if "mask.create_active" in step:
            step["mask.create_active"] = {"include_polygon": region_path}

    logging.debug("Injected region into config")

    # -----------------------------
    # 5. Initialize model
    # -----------------------------
    data_libs = cfg.get("global", {}).get("data_libs", [])
    # data_libs = ['c:/Git_repos/UFFFS/config/data_catalog.yml']

    logging.info(f"Using data libs: {data_libs}")

    sf = SfincsModel(
        data_libs=data_libs,
        root=str(model_root),
        mode="w+",
        write_gis=True,
    )

    logging.info("Initialized SfincsModel")
    logging.debug("Starting HydroMT build")

    sf.build(steps=cfg["steps"]) # 6. Build from YAML steps

    logging.debug("Build completed")

    sf.plot_basemap('basemap.png') # 7. Generate basemap for quick visual check of domain and data coverage
    logging.debug(f"Generated basemap at {os.path.join(model_root,'basemap.png')}")

    sf.write()
    logging.info("=== SFINCS build finished successfully ===")

# -----------------------------
# Standalone debug mode
# -----------------------------
if __name__ == "__main__":
    try:
        smk = snakemake
    except NameError:
        import yaml

        class FakeSnakemake:
            wildcards = type(
                "obj", (), {"city": "Kampala", "sfmodel": "kampala_sfincsmodel_01"}
            )()

            config = yaml.safe_load(open("config/cities.yaml"))
            log = ["debug_sfincs.log"]  # ✅ write log also in debug mode

        smk = FakeSnakemake()

    main(smk)
