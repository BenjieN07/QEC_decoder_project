import numpy as np
import pytest
from qec_project.config import load_config
from qec_project.baseline import generate, evaluate, wilson


@pytest.mark.parametrize('basis', ['X', 'Z'])
def test_noiseless(tmp_path, basis):
    config = load_config('configs/smoke.json')
    config['basis'] = basis
    config['noise'] = dict.fromkeys(config['noise'], 0.)
    result = evaluate(config, tmp_path, True)
    assert result['failures'] == 0
    assert result['mean_detected_events'] == 0
    assert result['ci_high'] > 0
    samples = np.load(tmp_path/'samples.npz')
    assert samples['actual'].shape == (1000, 1)
    assert samples['detectors'].shape == (1000, generate(config).num_detectors)


def test_repeatability_and_sinter(tmp_path):
    config = load_config('configs/smoke.json')
    evaluate(config, tmp_path/'a', True)
    evaluate(config, tmp_path/'b', True)
    a, b = (np.load(tmp_path/x/'samples.npz') for x in ('a', 'b'))
    for name in a.files:
        assert np.array_equal(a[name], b[name])


def test_interval():
    assert wilson(0, 100)[0] == 0
    assert wilson(100, 100)[1] == 1
    low, high = wilson(50, 100)
    assert low == pytest.approx(1-high)
    assert low < .5 < high
