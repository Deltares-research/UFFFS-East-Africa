from pathlib import Path
import logging
import sys
from os.path import join, exists
import yaml

import xarray as xr
from matplotlib import pyplot as plt
import geopandas as gpd

from hydromt_sfincs.utils import downscale_floodmap
from hydromt_sfincs import SfincsModel

from hydromt._utils import log as hydromt_log


def load_yaml(path):
    with open(path, "r", encoding="utf-8") as f:
        return yaml.safe_load(f) or {}

def get_base_model_root(base_cfg, city, sfmodel):
    sf_cfg = base_cfg["cities"][city]["sfincs"][sfmodel]
    return Path(sf_cfg.get("model_dir", f"outputs/{city}/sfincs_base/{sfmodel}"))

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

    mod = SfincsModel(model_root, mode='r')
    mod.output.read()
    da_zsmax = mod.output.data["zsmax"].max(dim="timemax")

    logging.info(f"Model root: {model_root}")
    logging.info(f"Floodmap output: {snakemake.output[0]}")
    if exists(join(model_root , "sfincs_his.nc" )):
        if "point_zs" in mod.output.data:
            plt.figure()
            mod.output.data["point_zs"].plot.line(x='time')
            plt.savefig(join(model_root , "sfincs_output_H.png" ))
        if "crosssection_discharge" in mod.output.data:
            plt.figure()
            mod.output.data["crosssection_discharge"].plot.line(x='time')
            plt.savefig(join(model_root , "sfincs_output_Q.png" ))

  
    kwargs = {}
    if "reproj_method" in pp:
        kwargs["reproj_method"] = pp["reproj_method"]
    if "zoom_level" in pp:
        kwargs["zoom_level"] = pp["zoom_level"]
    if "nrmax" in pp:
        kwargs["nrmax"] = pp["nrmax"]

    hmin = pp.get("hmin", 0.05)
    if "hmax" not in mod.output.data:
        downscale_floodmap(
            zsmax=da_zsmax,
            dep=str(dem_path),
            # indices=pp.get("indices"),
            hmin=hmin,
            # gdf_mask=gdf_mask,
            floodmap_fn=snakemake.output[0],
            **kwargs,
        )
        logging.info("Downscaled floodmap written successfully")
        logging.info("=== SFINCS postprocessing finished successfully ===")
    elif "hmax" in mod.output.data:
        logging.warning("No subgrid found in model, skipping downscaling of floodmap")
        da_hmax = mod.output.data["hmax"].max(dim="timemax").where(mod.output.data["hmax"].max(dim="timemax") > hmin)

        da_hmax.rio.to_raster(snakemake.output[0])
        logging.info("Floodmap written successfully")
        logging.info("=== SFINCS postprocessing finished successfully ===")

if __name__ == "__main__":
    try:
        smk = snakemake
    except NameError:
        class _WC:
            city = "Addis"
            event = "synthetic_60mm_6h"
            sfmodel = "addis_sfincsmodel_01"

        class FakeSnakemake:
            wildcards = _WC()

            input = type(
                "obj",
                (),
                {
                    "map": "outputs\\Addis\\events\\synthetic_60mm_6h\\addis_sfincsmodel_01\\sfincs_map.nc",
                    "events_cfg": "config/events.yml",
                    "base_cfg": "config/cities.yml",
                },
            )()

            output = [
                "outputs\\Addis\\events\\synthetic_60mm_6h\\addis_sfincsmodel_01\\floodmap.tif"
            ]

            log = [
                "logs/events/debug_post_Addis_synthetic_60mm_6h_addis_sfincsmodel_01.log"
            ]

        smk = FakeSnakemake()

    main(smk)

