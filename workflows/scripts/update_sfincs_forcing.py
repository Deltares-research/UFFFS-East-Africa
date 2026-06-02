from pathlib import Path
import logging
import sys
import yaml

from hydromt_sfincs import SfincsModel
from hydromt._utils import log as hydromt_log


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
    return Path(sf_cfg.get("model_dir", f"outputs/{city}/sfincs/{sfmodel}/base"))


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
        # Based on the documented create_uniform(timeseries=None, magnitude=None)
        # interface for spatially uniform precipitation forcing.
        if "timeseries" in forcing_cfg:
            sf.precipitation.create_uniform(timeseries=forcing_cfg["timeseries"])
            logging.info(f"Created uniform precipitation from timeseries: {forcing_cfg['timeseries']}")
        else:
            sf.precipitation.create_uniform(magnitude=forcing_cfg["magnitude"])
            logging.info(f"Created uniform precipitation with magnitude = {forcing_cfg['magnitude']} mm/hr")

    else:
        raise ValueError(
            f"Unsupported forcing.type '{forcing_type}'. "
            f"Use 'catalog' or 'synthetic_constant'."
        )

    sf.write()
    logging.info("Wrote updated event model")
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
                    "base_cfg": "config/cities.yaml",
                    "events_cfg": "config/events.yaml",
                },
            )()
            output = ["outputs/Kampala/events/synthetic_100mm_24h/kampala_sfincsmodel_01/model/sfincs.inp"]
            log = ["logs/events/debug_update_Kampala_synthetic_100mm_24h_kampala_sfincsmodel_01.log"]

        smk = FakeSnakemake()

    main(smk)