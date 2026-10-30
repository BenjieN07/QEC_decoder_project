import json
from pathlib import Path
import pytest
from qec_project.config import load_config
from qec_project.__main__ import main, write_manifest
from qec_project.__main__ import git_info

CONFIG = Path(__file__).resolve().parents[1] / "configs/smoke.json"


def test_manifest(tmp_path):
    config = load_config(CONFIG)
    config["output_dir"] = str(tmp_path / "nested")
    first = write_manifest(config)
    second = write_manifest(config)
    assert first != second
    manifest = json.loads(first.read_text())
    assert manifest["config"] == config
    assert manifest["seed"] == 42
    assert manifest["simulation_performed"] is False
    assert manifest["python"] and manifest["os"]
    assert "commit" in manifest["git"]
    assert "stim" in manifest["versions"]


@pytest.mark.parametrize("key,value", [
    ("basis", "Y"), ("distance", 4), ("distance", True),
    ("rounds", 0), ("shots", -1), ("seed", 2**64),
    ("decoder", "invented"), ("output_dir", ""), ("extra", 1),
])
def test_invalid_config(tmp_path, key, value):
    config = load_config(CONFIG)
    config[key] = value
    path = tmp_path / "bad.json"
    path.write_text(json.dumps(config))
    with pytest.raises(ValueError):
        load_config(path)


@pytest.mark.parametrize("value", [-0.1, 1.1, True, float("nan")])
def test_invalid_noise(tmp_path, value):
    config = load_config(CONFIG)
    config["noise"]["after_reset_flip_probability"] = value
    path = tmp_path / "bad.json"
    path.write_text(json.dumps(config))
    with pytest.raises(ValueError):
        load_config(path)


def test_help(capsys):
    with pytest.raises(SystemExit) as result:
        main(["--help"])
    assert result.value.code == 0
    assert "--smoke" in capsys.readouterr().out


def test_cli(tmp_path, capsys):
    config = load_config(CONFIG)
    config["output_dir"] = str(tmp_path)
    path = tmp_path / "config.json"
    path.write_text(json.dumps(config))
    main(["--smoke", "--config", str(path)])
    assert "no simulation performed" in capsys.readouterr().out
    assert len(list(tmp_path.glob("*/manifest.json"))) == 1


def test_missing_config(tmp_path, capsys):
    with pytest.raises(SystemExit) as result:
        main(["--smoke", "--config", str(tmp_path / "missing.json")])
    assert result.value.code == 2
    assert "error:" in capsys.readouterr().err


def test_git_unavailable(monkeypatch):
    def missing(*args, **kwargs):
        raise FileNotFoundError("git unavailable")
    monkeypatch.setattr("subprocess.check_output", missing)
    assert git_info() == {"commit": None, "status_porcelain": None}
