from pathlib import Path
import logging
import sys
import yaml

import xarray as xr
import geopandas as gpd

from hydromt_sfincs.utils import downscale_floodmap
from hydromt._utils import log as hydromt_log


def load_yaml(path):
    with open(path, "r", encoding="utf-8") as f:
        return yaml.safe_load(f) or {}

def get_base_model_root(base_cfg, city, sfmodel):
    sf_cfg = base_cfg["cities"][city]["sfincs"][sfmodel]
    return Path(sf_cfg.get("model_dir", f"outputs/{city}/sfincs/{sfmodel}/base"))

def setup_logging(log_file):
    handlers = [logging.StreamHandler(sys.stdout)]
    if log_file:
        Path(log_file).parent.mkdir(parents=True, exist_ok=True)
        handlers.append(logging.FileHandler(log_file))

    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s [%(levelname)s] %(message)s",
        handlers=handlers,
        force=True,
    )



def main(snakemake):
    log_file = snakemake.log[0] if hasattr(snakemake, "log") and len(snakemake.log) > 0 else None
    setup_logging(log_file)

    city = snakemake.wildcards.city
    event = snakemake.wildcards.event
    sfmodel = snakemake.wildcards.sfmodel

    logging.info("=== Starting SFINCS postprocessing ===")
    logging.info(f"City: {city}")
    logging.info(f"Event: {event}")
    logging.info(f"Model: {sfmodel}")
    
    base_cfg = load_yaml(snakemake.input.base_cfg)
    event_cfg = load_yaml(snakemake.input.events_cfg)
    ev = event_cfg["cities"][city]["events"][event]
    pp = ev["postprocess"]

    
    base_model_root = get_base_model_root(base_cfg, city, sfmodel)
    model_root = Path(snakemake.input.map).parent
    post_root = Path(snakemake.output[0]).parent
    post_root.mkdir(parents=True, exist_ok=True)
    dem_path = base_model_root / "subgrid" / "dep_subgrid.tif"

    if not dem_path.exists():
        raise FileNotFoundError(
            f"DEM not found in base model folder: {dem_path}"
        )


    map_file = pp.get("map_file", "sfincs_map.nc")
    zsmax_var = pp.get("zsmax_var", "zs")
    map_path = model_root / map_file

    logging.info(f"Model root: {model_root}")
    logging.info(f"Map file: {map_path}")
    logging.info(f"Floodmap output: {snakemake.output[0]}")

    if not map_path.exists():
        raise FileNotFoundError(
            f"Expected model output file not found: {map_path}. "
            f"Adjust postprocess.map_file in config/events.yaml if needed."
        )

    ds = xr.open_dataset(map_path)
    if zsmax_var not in ds:
        raise KeyError(
            f"Variable '{zsmax_var}' not found in {map_path}. "
            f"Adjust postprocess.zsmax_var in config/events.yaml."
        )

    zsmax = ds[zsmax_var]

    gdf_mask = None
    if "mask" in pp and pp["mask"]:
        gdf_mask = gpd.read_file(pp["mask"])
        logging.info(f"Loaded mask polygons from: {pp['mask']}")

    kwargs = {}
    if "reproj_method" in pp:
        kwargs["reproj_method"] = pp["reproj_method"]
    if "zoom_level" in pp:
        kwargs["zoom_level"] = pp["zoom_level"]
    if "nrmax" in pp:
        kwargs["nrmax"] = pp["nrmax"]

    downscale_floodmap(
        zsmax=zsmax,
        dep=str(dem_path),
        # indices=pp.get("indices"),
        hmin=pp.get("hmin", 0.05),
        # gdf_mask=gdf_mask,
        floodmap_fn=snakemake.output[0],
        **kwargs,
    )

    logging.info("Downscaled floodmap written successfully")
    logging.info("=== SFINCS postprocessing finished successfully ===")


if __name__ == "__main__":
    try:
        smk = snakemake
    except NameError:
        class _WC:
            city = "Kampala"
            event = "synthetic_100mm_24h"
            sfmodel = "kampala_sfincsmodel_01"

        class FakeSnakemake:
            wildcards = _WC()

            input = type(
                "obj",
                (),
                {
                    # ✅ updated: use sfincs_map.nc instead of .ran
                    "map": "outputs/Kampala/events/synthetic_100mm_24h/kampala_sfincsmodel_01/model/sfincs_map.nc",
                    "events_cfg": "config/events.yml",
                    "base_cfg": "config/cities.yaml",
                },
            )()

            output = [
                "outputs/Kampala/events/synthetic_100mm_24h/kampala_sfincsmodel_01/post/floodmap.tif"
            ]

            log = [
                "logs/events/debug_post_Kampala_synthetic_100mm_24h_kampala_sfincsmodel_01.log"
            ]

        smk = FakeSnakemake()

    main(smk)

