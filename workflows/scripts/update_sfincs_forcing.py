from pathlib import Path
import logging
import sys
import yaml

from hydromt_sfincs import SfincsModel
from hydromt._utils import log as hydromt_log

from pathlib import Path
import os
import shutil
import logging

# Files that belong to the static model schematisation and should be reused
STATIC_MODEL_FILES = [
    "sfincs.dep",
    "sfincs.msk",
    "sfincs.ind",
    "sfincs.man",
    "sfincs.qinf",
    "sfincs.scs",
    "sfincs.smax",
    "sfincs.seff",
    "sfincs.ks",
    "sfincs.obs",
    "sfincs.thd",
    "sfincs.weir",
    "sfincs.drn",
    "sfincs_subgrid.nc",
    "gis/dep.tif",   # if HydroMT writes GIS sidecar data you want to dep.tif
    "gis/manning.tif",   # if HydroMT writes GIS sidecar data you want to dep.tif
    "gis/mask.tif",   # if HydroMT writes GIS sidecar data you want to dep.tif
    "gis/region.geojson",   # if HydroMT writes GIS sidecar data you want to dep.tif
]

# Files that are event-specific and should remain local in the event folder
EVENT_LOCAL_FILES = {
    "sfincs.inp",
    "sfincs.prcp",
    "sfincs_netampr.nc",
    "sfincs_map.nc",
    "sfincs_his.nc",
    "hydromt_sfincs.log",
}

def _remove_path(path: Path):
    if not path.exists() and not path.is_symlink():
        return
    if path.is_dir() and not path.is_symlink():
        shutil.rmtree(path)
    else:
        path.unlink()

def link_or_copy(src: Path, dst: Path):
    """
    Prefer hardlink, then symlink, then copy as fallback.
    Hardlinks avoid duplication and work well on the same filesystem.
    """
    dst.parent.mkdir(parents=True, exist_ok=True)

    if dst.exists() or dst.is_symlink():
        _remove_path(dst)

    if src.is_dir():
        # safest for directories: symlink if possible, else copytree
        try:
            os.symlink(src, dst, target_is_directory=True)
            return "symlink"
        except Exception:
            shutil.copytree(src, dst)
            return "copydir"

    # file case
    try:
        os.link(src, dst)
        return "hardlink"
    except Exception:
        try:
            os.symlink(src, dst)
            return "symlink"
        except Exception:
            shutil.copy2(src, dst)
            return "copy"

def load_yaml(path):
    with open(path, "r", encoding="utf-8") as f:
        return yaml.safe_load(f) or {}


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

    hydromt_log.initialize_logging()
    if log_file:
        hydromt_log._add_filehandler(log_file)


def get_base_model_root(base_cfg, city, sfmodel):
    sf_cfg = base_cfg["cities"][city]["sfincs"][sfmodel]
    return Path(sf_cfg.get("model_dir", f"outputs/{city}/sfincs_base/{sfmodel}"))


def main(snakemake):
    log_file = snakemake.log[0] if hasattr(snakemake, "log") and len(snakemake.log) > 0 else None
    setup_logging(log_file)

    city = snakemake.wildcards.city
    event = snakemake.wildcards.event
    sfmodel = snakemake.wildcards.sfmodel

    logging.info("=== Starting event update ===")
    logging.info(f"City: {city}")
    logging.info(f"Event: {event}")
    logging.info(f"Model: {sfmodel}")

    base_cfg = load_yaml(snakemake.input.base_cfg)
    event_cfg = load_yaml(snakemake.input.events_cfg)

    ev = event_cfg["cities"][city]["events"][event]
    forcing_cfg = ev["forcing"]

    model_root_in = get_base_model_root(base_cfg, city, sfmodel)
    model_root_out = Path(snakemake.output[0]).parent

    logging.info(f"Base model root: {model_root_in}")
    logging.info(f"Event model root: {model_root_out}")
    logging.info(f"Forcing config: {forcing_cfg}")

    data_libs = event_cfg.get("global", {}).get("data_libs", [])
    if isinstance(data_libs, str):
        data_libs = [data_libs]

    # Open existing model in read mode, then switch output root to a new folder
    sf = SfincsModel(
        data_libs=data_libs,
        root=str(model_root_in),
        mode="r",
        write_gis=True,
    )
    sf.read()
    sf.root.set(str(model_root_out), mode="w+")

    # Update model timing
    sf.config.update(
        {
            "tref": ev["start"],
            "tstart": ev["start"],
            "tstop": ev["end"],
        }
    )
    logging.info("Updated tref/tstart/tstop")

    forcing_type = forcing_cfg["type"]
    

    if forcing_type == "catalog":
        # Based on the documented update flow using sf.precipitation.create(...)
        # and the documented parameters of the precipitation.create API.
        kwargs = {}
        for key in ["dst_res", "cumulative_input", "time_label", "aggregate"]:
            if key in forcing_cfg:
                kwargs[key] = forcing_cfg[key]

        sf.precipitation.create(
            precip=forcing_cfg["precip"],
            **kwargs,
        )
        logging.info(f"Created precipitation forcing from catalog source: {forcing_cfg['precip']}")

    elif forcing_type == "synthetic_constant":
        # Use spatially uniform precipitation forcing

        if "precipitation_mm_per_hr" not in forcing_cfg:
            raise ValueError(
                "synthetic_constant forcing requires 'precipitation_mm_per_hr'"
            )

        magnitude = forcing_cfg["precipitation_mm_per_hr"]

        sf.precipitation.create_uniform(magnitude=magnitude)

        logging.info(
            f"Created uniform precipitation forcing: {magnitude} mm/hr"
        )

    else:
        raise ValueError(
            f"Unsupported forcing.type '{forcing_type}'. "
            f"Use 'catalog' or 'synthetic_constant'."
        )

    if "discharge" in forcing_cfg:
        dis_cfg = forcing_cfg["discharge"]
        sf.discharge_points.create(
            timeseries=dis_cfg["timeseries"],
            locations=dis_cfg["locations"],
        )
        logging.info("Created discharge forcing from locations/timeseries")

    sf.write()
    logging.info("Wrote updated event model")
    # -----------------------------------------------------------------
    # Replace duplicated static files in the event folder with links
    # to the base model folder
    # -----------------------------------------------------------------
    base_root = Path(model_root_in)
    event_root = Path(model_root_out)

    for name in STATIC_MODEL_FILES:
        src = base_root / name
        dst = event_root / name

        if not src.exists():
            continue

        if name in EVENT_LOCAL_FILES:
            continue

        mode = link_or_copy(src, dst)
        logging.debug(f"Reused static model asset '{name}' using mode: {mode}")

    
    logging.info("=== Event update finished successfully ===")


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
                    "base_cfg": "config/cities.yml",
                    "events_cfg": "config/events.yml",
                },
            )()
            output = ["outputs/Kampala/events/synthetic_100mm_24h/kampala_sfincsmodel_01/model/sfincs.inp"]
            log = ["logs/events/debug_update_Kampala_synthetic_100mm_24h_kampala_sfincsmodel_01.log"]

        smk = FakeSnakemake()

    main(smk)