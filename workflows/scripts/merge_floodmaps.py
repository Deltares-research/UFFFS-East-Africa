from pathlib import Path
import logging
import sys
import shutil
import rasterio
from rasterio.merge import Resampling, merge
from rasterio.io import MemoryFile
import numpy as np
from rasterio.warp import reproject, Resampling
from rasterio.transform import from_origin


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
        logging.info("Only one floodmap: copied directly")
        return

        # ✅ Case 2: multiple models → merge
    logging.info("Merging floodmaps using max()")

    srcs = []
    memfiles = []

    for fp in floodmaps:
        src = rasterio.open(fp)

        transform = src.transform

        # detect upside-down raster
        if transform.e > 0:
            logging.info(f"{fp.name}: upside-down raster: flipping")

            data = src.read()[:, ::-1, :]

            new_transform = rasterio.Affine(
                transform.a,
                transform.b,
                transform.c,
                transform.d,
                -transform.e,
                transform.f + transform.e * src.height,
            )

            profile = src.profile.copy()
            profile.update(transform=new_transform)

            memfile = MemoryFile()
            dst = memfile.open(**profile)
            dst.write(data)

            memfiles.append(memfile)
            srcs.append(dst)

        else:
            srcs.append(src)

    try:

        # ------------------------------------------------------------------
        # Determine union extent
        # ------------------------------------------------------------------
        left = min(src.bounds.left for src in srcs)
        right = max(src.bounds.right for src in srcs)
        bottom = min(src.bounds.bottom for src in srcs)
        top = max(src.bounds.top for src in srcs)

        # use finest resolution
        res_x = min(abs(src.transform.a) for src in srcs)
        res_y = min(abs(src.transform.e) for src in srcs)

        width = int(np.ceil((right - left) / res_x))
        height = int(np.ceil((top - bottom) / res_y))

        transform = rasterio.transform.from_origin(
            left,
            top,
            res_x,
            res_y,
        )

        combined = np.full((height, width), np.nan, dtype=np.float32)

        # ------------------------------------------------------------------
        # Reproject each floodmap onto common grid and take maximum
        # ------------------------------------------------------------------
        for src in srcs:

            arr = np.full((height, width), np.nan, dtype=np.float32)

            reproject(
                source=rasterio.band(src, 1),
                destination=arr,
                src_transform=src.transform,
                src_crs=src.crs,
                dst_transform=transform,
                dst_crs=src.crs,
                src_nodata=src.nodata,
                dst_nodata=np.nan,
                resampling=Resampling.nearest,
            )

            # Optional flood threshold
            arr[arr < 0.05] = np.nan

            combined = np.fmax(combined, arr)

        nodata = -9999.0
        combined[np.isnan(combined)] = nodata

        out_meta = srcs[0].meta.copy()
        out_meta.update(
            {
                "driver": "GTiff",
                "height": height,
                "width": width,
                "transform": transform,
                "count": 1,
                "dtype": "float32",
                "nodata": nodata,
                "compress": "deflate",
            }
        )

        with rasterio.open(out_path, "w", **out_meta) as dest:
            dest.write(combined.astype(np.float32), 1)

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