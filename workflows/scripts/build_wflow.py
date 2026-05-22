#!/usr/bin/env python
import argparse
import subprocess
from pathlib import Path
import yaml

def deep_merge(a, b):
    """Recursively merge dict b into dict a (a is copied)."""
    out = dict(a) if isinstance(a, dict) else {}
    for k, v in (b or {}).items():
        if isinstance(v, dict) and isinstance(out.get(k), dict):
            out[k] = deep_merge(out[k], v)
        else:
            out[k] = v
    return out

def main():
    p = argparse.ArgumentParser()
    p.add_argument("--config", required=True)
    p.add_argument("--city", required=True)
    args = p.parse_args()

    cfg = yaml.safe_load(Path(args.config).read_text())
    city_cfg = cfg["cities"][args.city]
    catalog = cfg.get("data_catalog", "resources/data_catalog.yml")

    wcfg = city_cfg["wflow"]
    outdir = Path(wcfg.get("model_dir", f"outputs/{args.city}/wflow/base")).resolve()
    outdir.mkdir(parents=True, exist_ok=True)

    region = wcfg["region"]
    build_template = wcfg["build_config"]            # e.g. config/templates/wflow/build.yml
    build_overrides = wcfg.get("build_overrides")    # e.g. cities/<city>/params/wflow_overrides.yml

    base = yaml.safe_load(Path(build_template).read_text())
    overrides = yaml.safe_load(Path(build_overrides).read_text()) if build_overrides else {}
    merged = deep_merge(base, overrides)

    merged_cfg_path = outdir / "_hydromt_build_wflow.yml"
    merged_cfg_path.write_text(yaml.safe_dump(merged, sort_keys=False))

    # HydroMT-Wflow CLI build pattern (example command structure) is documented. [4](https://deepwiki.com/Deltares/hydromt_wflow/5-model-building)
    cmd = [
        "hydromt", "build", "wflow",
        str(outdir),
        "-r", str(region),
        "-i", str(merged_cfg_path),
        "-d", str(catalog),
        "-vv"
    ]

    print("Running:", " ".join(cmd))
    subprocess.run(cmd, check=True)

    (outdir / ".built").touch()

if __name__ == "__main__":
    main()