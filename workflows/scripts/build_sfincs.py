from pathlib import Path
import yaml
import logging
import sys
import copy
import os

from hydromt_sfincs import SfincsModel


def main(snakemake):
    # -----------------------------
    # 0. Setup logging
    # -----------------------------
    log_file = snakemake.log[0] if getattr(snakemake, "log", []) else None

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

    logging.debug("=== Starting SFINCS build script===")

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

    model_root = Path(snakemake.output["model_root"]).parent
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

    def merge(base_cfg, override_cfg):
        """
        Merge override_cfg into base_cfg.

        Supported pattern in override YAML:
        some_key:
            override: ...
            add: ...
        """

        def step_key(step):
            return list(step.keys())[0]

        def merge_steps(base_steps, step_ops):
            """
            step_ops can be:
            - plain list          -> append all (backwards compatible)
            - {override: [...], add: [...]}
            """
            steps = copy.deepcopy(base_steps or [])

            # Backwards compatible: plain list = add
            if isinstance(step_ops, list):
                return steps + copy.deepcopy(step_ops)
            if not isinstance(step_ops, dict):
                raise TypeError(
                    f"steps override must be list or dict, got {type(step_ops)}"
                )

            # 1. override existing step(s) by method name
            for new_step in step_ops.get("override", []):
                new_key = step_key(new_step)

                replaced = False
                for i, old_step in enumerate(steps):
                    if step_key(old_step) == new_key:
                        steps[i] = copy.deepcopy(new_step)
                        replaced = True
                        break
                if not replaced:
                    # if step not present yet, append it
                    steps.append(copy.deepcopy(new_step))

            # 2. append add-steps (duplicates allowed)
            for add_step in step_ops.get("add", []):
                steps.append(copy.deepcopy(add_step))
            return steps

        def _merge(a, b):
            out = copy.deepcopy(a)
            for k, v in (b or {}).items():
                # -----------------------------
                # Special case: steps
                # -----------------------------
                if k == "steps":
                    out["steps"] = merge_steps(out.get("steps", []), v)
                # -----------------------------
                # Generic add/override blocks
                # -----------------------------
                elif isinstance(v, dict) and ("add" in v or "override" in v):
                    base_val = out.get(k)

                    # override part
                    if "override" in v:
                        ov = v["override"]
                        if isinstance(base_val, dict) and isinstance(ov, dict):
                            out[k] = _merge(base_val, ov)
                        else:
                            out[k] = copy.deepcopy(ov)
                    # add part
                    if "add" in v:
                        add_val = v["add"]
                        if k not in out:
                            out[k] = copy.deepcopy(add_val)
                        elif isinstance(out[k], list) and isinstance(add_val, list):
                            out[k] = out[k] + copy.deepcopy(add_val)
                        elif isinstance(out[k], dict) and isinstance(add_val, dict):
                            # for dicts, "add" behaves like update
                            tmp = copy.deepcopy(out[k])
                            tmp.update(copy.deepcopy(add_val))
                            out[k] = tmp
                        else:
                            raise TypeError(
                                f"Cannot apply add-operation to key '{k}' of type {type(out[k])}"
                            )

                # -----------------------------
                # Default recursive merge
                # -----------------------------
                elif k in out and isinstance(out[k], dict) and isinstance(v, dict):
                    out[k] = _merge(out[k], v)

                else:
                    out[k] = copy.deepcopy(v)

            return out

        return _merge(base_cfg, override_cfg)

    def call_step(sf, step):
        name, kwargs = next(iter(step.items()))
        kwargs = kwargs or {}

        component, method = name.split(".")
        getattr(getattr(sf, component), method)(**kwargs)

    cfg = merge(base, overrides)

    logging.debug("Merged base and override configs")
    # -----------------------------
    # 4. Inject region
    # -----------------------------
    for step in cfg["steps"]:
        if "grid.create_from_region" in step:
            v = step["grid.create_from_region"]
            if isinstance(v, str):
                step["grid.create_from_region"] = {"region": v}
            elif v is None:
                step["grid.create_from_region"] = {}
            step["grid.create_from_region"]["region"] = {"geom": region_path}
        if "mask.create_active" in step:
            v = step["mask.create_active"]
            if isinstance(v, str):
                # convert shorthand to dict
                step["mask.create_active"] = {"include_polygon": v}
            elif v is None:
                step["mask.create_active"] = {}
            # now safe to assign
            step["mask.create_active"]["include_polygon"] = region_path

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

    logging.debug("Initialized SfincsModel")

    for step in cfg["steps"]:
        logging.debug(f"Running step: {next(iter(step))}")
        call_step(sf, step)

    sf.plot_basemap(
        "basemap.png"
    )  # 7. Generate basemap for quick visual check of domain and data coverage
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
        from pathlib import Path

        class FakeSnakemake:
            def __init__(self):
                self.wildcards = type(
                    "obj",
                    (),
                    {"city": "Juba", "sfmodel": "juba_sfincsmodel_01"},
                )()

                self.config = yaml.safe_load(open("config/cities.yml"))

                # MUST include this
                self.output = {
                    "model_root": "outputs/Juba/sfincs_base/juba_sfincsmodel_01/sfincs.inp"
                }

                # Must behave like list
                self.log = ["logs/debug_sfincs.log"]

        smk = FakeSnakemake()

    main(smk)
