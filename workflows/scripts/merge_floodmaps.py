from pathlib import Path
import logging
import sys
import shutil
import rasterio
from rasterio.merge import merge


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

    floodmaps = [Path(p) for p in snakemake.input]
    out_path = Path(snakemake.output[0])
    out_path.parent.mkdir(parents=True, exist_ok=True)

    logging.info("=== Combining floodmaps ===")
    logging.info(f"City: {city}")
    logging.info(f"Event: {event}")
    logging.info(f"Number of input floodmaps: {len(floodmaps)}")

    for fp in floodmaps:
        logging.info(f"  - {fp}")

    # ❗ Check existence
    for fp in floodmaps:
        if not fp.exists():
            raise FileNotFoundError(f"Missing floodmap: {fp}")

    # ✅ Case 1: only one model → copy
    if len(floodmaps) == 1:
        shutil.copy2(floodmaps[0], out_path)
        logging.info("Only one floodmap → copied directly")
        return

    # ✅ Case 2: multiple models → merge
    logging.info("Merging floodmaps using max()")

    srcs = [rasterio.open(fp) for fp in floodmaps]

    try:
        mosaic, transform = merge(srcs, method="max")

        out_meta = srcs[0].meta.copy()
        out_meta.pop("profile", None)
        out_meta.update(
            {
                "height": mosaic.shape[1],
                "width": mosaic.shape[2],
                "transform": transform,
            }
        )

        with rasterio.open(out_path, "w", **out_meta) as dest:
            dest.write(mosaic)

    finally:
        for src in srcs:
            src.close()

    logging.info("Merged floodmap written successfully")


if __name__ == "__main__":
    try:
        smk = snakemake
    except NameError:
        class _WC:
            city = "Kampala"
            event = "synthetic_100mm_24h"

        class FakeSnakemake:
            wildcards = _WC()
            input = [
                "outputs/Kampala/events/synthetic_100mm_24h/kampala_sfincsmodel_01/floodmap.tif",
                # add a second file here if you want to test merging
            ]
            output = [
                "outputs/Kampala/events/synthetic_100mm_24h/floodmap.tif"
            ]
            log = [
                "logs/events/debug_merge_Kampala_synthetic_100mm_24h.log"
            ]

        smk = FakeSnakemake()

    main(smk)