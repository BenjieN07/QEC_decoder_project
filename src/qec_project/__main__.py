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
    import sys
    argv = list(sys.argv[1:] if argv is None else argv)
    if argv and argv[0] == 'compare':
        parser = argparse.ArgumentParser(description='M3 paired predecoder comparison')
        parser.add_argument('mode')
        parser.add_argument('--replay', type=Path, required=True)
        args = parser.parse_args(argv)
        from .predecoder import compare
        return compare(args.replay)
    if argv and argv[0] == 'benchmark':
        parser = argparse.ArgumentParser(description='M2 fixed-sample CPU workload replay')
        parser.add_argument('mode')
        parser.add_argument('--replay', type=Path, required=True, help='M1 per-point directory')
        args = parser.parse_args(argv)
        from .workload import benchmark
        return benchmark(args.replay)
    if argv and argv[0] in ('demo', 'sweep'):
        return experiment_cli(argv)
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


def experiment_cli(argv):
    import copy
    parser = argparse.ArgumentParser(description='Offline Stim/PyMatching memory experiment')
    parser.add_argument('mode', choices=['demo', 'sweep'])
    parser.add_argument('--config', type=Path, default=Path('configs/smoke.json'))
    parser.add_argument('--distance', type=int, default=3)
    parser.add_argument('--rounds', type=int, default=3)
    parser.add_argument('--basis', choices=['X', 'Z'], default='X')
    parser.add_argument('--p', type=float, default=.005)
    parser.add_argument('--shots', type=int, default=1000)
    parser.add_argument('--seed', type=int, default=42)
    parser.add_argument('--crosscheck', action='store_true')
    args = parser.parse_args(argv)
    try:
        from .baseline import run
        config = load_config(args.config)
        configs = []
        if args.mode == 'demo':
            if not 0 <= args.p <= 1 or args.distance < 3 or args.distance % 2 != 1 or args.rounds < 1 or args.shots < 1 or not 0 <= args.seed < 2**64:
                raise ValueError('invalid probability, odd distance >=3, rounds, shots or seed')
            config.update(distance=args.distance, rounds=args.rounds, basis=args.basis,
                          shots=args.shots, seed=args.seed)
            config['noise'] = dict.fromkeys(config['noise'], args.p)
            configs.append(config)
        else:
            for basis in ('X', 'Z'):
                for distance in (3, 5, 7):
                    for p in (.001, .003, .005):
                        item = copy.deepcopy(config)
                        item.update(basis=basis, distance=distance, rounds=distance)
                        item['noise'] = dict.fromkeys(item['noise'], p)
                        configs.append(item)
        run(configs, args.crosscheck)
    except ImportError as error:
        parser.error(f'{error}; install the research extra: pip install -e ".[research]"')
    except (ValueError, OSError) as error:
        parser.error(str(error))


if __name__ == "__main__":
    main()
