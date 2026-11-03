"""Offline surface-code memory experiments; observable-frame scoring."""
import csv
import json
import math
from pathlib import Path
from time import perf_counter

import numpy as np
import stim
import pymatching

from .__main__ import write_manifest


def wilson(failures, shots):
    if not 0 <= failures <= shots or shots <= 0:
        raise ValueError("require 0 <= failures <= shots and shots > 0")
    z = 1.959963984540054
    p = failures / shots
    denominator = 1 + z*z/shots
    center = (p + z*z/(2*shots))/denominator
    radius = z*math.sqrt(p*(1-p)/shots + z*z/(4*shots*shots))/denominator
    return (0. if failures == 0 else max(0., center-radius),
            1. if failures == shots else min(1., center+radius))


def generate(config):
    return stim.Circuit.generated(
        f"surface_code:rotated_memory_{config['basis'].lower()}",
        distance=config['distance'], rounds=config['rounds'], **config['noise'])


def evaluate(config, directory, crosscheck=False):
    start = perf_counter()
    circuit = generate(config)
    dem = circuit.detector_error_model(decompose_errors=True)
    matching = pymatching.Matching.from_detector_error_model(dem)
    detectors, actual = circuit.compile_detector_sampler(seed=config['seed']).sample(
        config['shots'], separate_observables=True)
    predicted = matching.decode_batch(detectors)
    failures = int(np.any(predicted != actual, axis=1).sum())
    low, high = wilson(failures, config['shots'])
    check = None
    if crosscheck:
        import sinter
        independent = sinter.predict_observables(
            dem=dem, dets=detectors, decoder='pymatching')
        check = bool(np.array_equal(independent, predicted))
        if not check:
            raise RuntimeError('Sinter predictions disagree on identical samples')
    directory = Path(directory)
    directory.mkdir(parents=True, exist_ok=True)
    (directory/'circuit.stim').write_text(str(circuit), encoding='utf-8')
    (directory/'model.dem').write_text(str(dem), encoding='utf-8')
    (directory/'config.json').write_text(json.dumps(config, indent=2), encoding='utf-8')
    np.savez_compressed(directory/'samples.npz', detectors=detectors,
                        actual=actual, predicted=predicted)
    row = dict(basis=config['basis'], distance=config['distance'], rounds=config['rounds'],
               shots=config['shots'], seed=config['seed'], decoder=config['decoder'],
               noise=json.dumps(config['noise'], sort_keys=True),
               p=config['noise']['after_clifford_depolarization'],
               detector_count=circuit.num_detectors, failures=failures,
               logical_failure_rate=failures/config['shots'], ci_low=low, ci_high=high,
               mean_detected_events=float(detectors.sum(axis=1).mean()),
               elapsed_seconds=perf_counter()-start, sinter_same_sample_agreement=check)
    (directory/'summary.json').write_text(json.dumps(row, indent=2), encoding='utf-8')
    return row


def plot(rows, path):
    import matplotlib
    matplotlib.use('Agg')
    import matplotlib.pyplot as plt
    fig, ax = plt.subplots()
    for basis, distance in sorted({(r['basis'], r['distance']) for r in rows}):
        points = sorted((r for r in rows if (r['basis'], r['distance']) == (basis, distance)),
                        key=lambda r: r['p'])
        y = np.array([r['logical_failure_rate'] for r in points])
        ax.errorbar([r['p'] for r in points], y,
                    yerr=[y-np.array([r['ci_low'] for r in points]),
                          np.array([r['ci_high'] for r in points])-y],
                    marker='o', label=f'{basis}, d={distance}')
    ax.set(xlabel='p (each of four circuit noise channels)',
           ylabel='Logical failure probability per memory experiment',
           title='Offline MWPM memory experiment (95% Wilson intervals)')
    ax.legend(); ax.grid(alpha=.3)
    fig.tight_layout(); fig.savefig(path); plt.close(fig)


def run(configs, crosscheck=False):
    manifest = write_manifest(configs[0])
    directory = manifest.parent
    data = json.loads(manifest.read_text())
    data.update(mode='baseline', simulation_performed=True, configs=configs)
    manifest.write_text(json.dumps(data, indent=2), encoding='utf-8')
    rows = []
    for index, config in enumerate(configs):
        row = evaluate(config, directory/str(index), crosscheck)
        rows.append(row)
        print(f"{config['basis']} d={config['distance']} rounds={config['rounds']} "
              f"failures={row['failures']}/{row['shots']} P_L={row['logical_failure_rate']:.6g} "
              f"95% CI=[{row['ci_low']:.6g}, {row['ci_high']:.6g}]")
    with (directory/'stats.csv').open('w', newline='', encoding='utf-8') as file:
        writer = csv.DictWriter(file, fieldnames=rows[0].keys())
        writer.writeheader(); writer.writerows(rows)
    plot(rows, directory/'logical_error_vs_physical_error.png')
    print(f'Outputs: {directory}')
    return directory
