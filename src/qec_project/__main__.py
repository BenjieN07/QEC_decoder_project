"""A smoke run records provenance only; no decoding occurs in M0."""
import argparse
from datetime import datetime, timezone
import importlib.metadata
import json
from pathlib import Path
import platform
import subprocess
from uuid import uuid4

from .config import load_config


def git_info():
    root = Path(__file__).resolve().parents[2]
    def run(*args):
        try:
            return subprocess.check_output(
                ["git", "-C", str(root), *args], text=True,
                stderr=subprocess.DEVNULL, timeout=5).strip()
        except (OSError, subprocess.SubprocessError):
            return None
    return {"commit": run("rev-parse", "HEAD"),
            "status_porcelain": run("status", "--porcelain")}


def write_manifest(config):
    versions = {}
    for name in ("qec-project", "stim", "pymatching", "sinter", "numpy", "pytest"):
        try:
            versions[name] = importlib.metadata.version(name)
        except importlib.metadata.PackageNotFoundError:
            versions[name] = None
    directory = Path(config["output_dir"]) / uuid4().hex
    directory.mkdir(parents=True, exist_ok=False)
    manifest = {"schema_version": 1, "mode": "infrastructure_smoke",
                "simulation_performed": False,
                "created_utc": datetime.now(timezone.utc).isoformat(),
                "config": config, "seed": config["seed"],
                "os": platform.platform(), "machine": platform.machine(),
                "python": platform.python_version(), "versions": versions,
                "git": git_info()}
    path = directory / "manifest.json"
    path.write_text(json.dumps(manifest, indent=2) + "\n", encoding="utf-8")
    return path


def main(argv=None):
    parser = argparse.ArgumentParser(description="M0 reproducibility infrastructure; no QEC simulation yet")
    parser.add_argument("--config", type=Path, default=Path("configs/smoke.json"))
    parser.add_argument("--smoke", action="store_true", help="validate settings and write an environment manifest")
    args = parser.parse_args(argv)
    if not args.smoke:
        parser.error("specify --smoke; experiment commands arrive in M1")
    try:
        path = write_manifest(load_config(args.config))
    except (OSError, ValueError) as error:
        parser.error(str(error))
    print(f"Infrastructure smoke passed; no simulation performed. Manifest: {path}")


if __name__ == "__main__":
    main()
