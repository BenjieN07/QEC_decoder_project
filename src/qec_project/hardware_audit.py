"""Offline H1 diagnostics. No cloud client, credentials, fitting or job submission."""
import argparse
import hashlib
import json
from pathlib import Path

import numpy as np
import pymatching
import stim

from .baseline import wilson
from .statistics import paired_interval


def correction_counts(actual, predicted):
    """Compare MWPM with the zero-frame prediction on identical memory shots."""
    actual = np.asarray(actual, dtype=bool)
    predicted = np.asarray(predicted, dtype=bool)
    if actual.ndim != 2 or actual.shape != predicted.shape or not len(actual):
        raise ValueError('require equal nonempty shot-by-observable arrays')
    raw_wrong = actual.any(axis=1)
    decoded_wrong = (actual != predicted).any(axis=1)
    helped = int((raw_wrong & ~decoded_wrong).sum())
    hurt = int((~raw_wrong & decoded_wrong).sum())
    return dict(shots=len(actual), zero_frame_failures=int(raw_wrong.sum()),
                decoded_failures=int(decoded_wrong.sum()), helped=helped, hurt=hurt,
                both_wrong=int((raw_wrong & decoded_wrong).sum()),
                both_correct=int((~raw_wrong & ~decoded_wrong).sum()),
                decoded_minus_zero_frame_ci=list(paired_interval(helped, hurt, len(actual))))


def audit(source, output, shots=50000, seed=20261107):
    if shots < 1:
        raise ValueError('simulation shots must be positive')
    source, output = Path(source), Path(output)
    preparation = json.loads((source/'preparation.json').read_text())
    rows = []
    hashes = {}
    for index, basis in enumerate(('X', 'Z')):
        for suffix in ('.stim', '.dem', '-measurements.npz'):
            path = source/(basis+suffix)
            hashes[path.name] = hashlib.sha256(path.read_bytes()).hexdigest()
        circuit = stim.Circuit((source/(basis+'.stim')).read_text())
        dem = stim.DetectorErrorModel((source/(basis+'.dem')).read_text())
        matching = pymatching.Matching.from_detector_error_model(dem)
        with np.load(source/(basis+'-measurements.npz'), allow_pickle=False) as data:
            dets, actual = circuit.compile_m2d_converter().convert(
                measurements=data['raw_measurements'], separate_observables=True)
            predicted = matching.decode_batch(dets)
            if not (np.array_equal(dets, data['detectors']) and
                    np.array_equal(actual, data['actual']) and
                    np.array_equal(predicted, data['baseline'])):
                raise ValueError('archived measurement conversion or baseline prediction mismatch')
            variants_equal = {name: bool(np.array_equal(predicted, data[name]))
                              for name in ('isolated', 'max2', 'guarded')}
        # Sample the archived prior itself: it is the decoder's assumed distribution,
        # not a calibrated simulation of the routed physical circuit.
        sd, sa = dem.compile_sampler(seed=seed+index).sample(shots=shots, return_errors=False)[:2]
        sp = matching.decode_batch(sd)
        coords = circuit.get_detector_coordinates()
        per_detector = []
        for detector in range(dets.shape[1]):
            count = int(dets[:, detector].sum())
            per_detector.append(dict(detector=detector, coordinates=coords[detector],
                                     observed_fraction=count/len(dets),
                                     observed_ci=list(wilson(count, len(dets))),
                                     prior_fraction=float(sd[:, detector].mean())))
        abstract_cx = sum(len(op.targets_copy())//2 for op in circuit.flattened() if op.name == 'CX')
        routed = next(c for c in preparation['circuits'] if c['basis'] == basis)
        groups = []
        events = dets.sum(axis=1)
        for low, high in ((0, 3), (4, 7), (8, 11), (12, 24)):
            selected = (events >= low) & (events <= high)
            if selected.any():
                group = correction_counts(actual[selected], predicted[selected])
                group['event_range'] = [low, high]
                groups.append(group)
        rows.append(dict(basis=basis, replay_verified=True, variants_equal=variants_equal,
                         physical=correction_counts(actual, predicted),
                         prior_simulation=correction_counts(sa, sp),
                         observed_mean_events=float(events.mean()),
                         prior_mean_events=float(sd.sum(axis=1).mean()),
                         abstract_cx=abstract_cx, routed_cz=routed['operations']['cz'],
                         routed_cz_per_abstract_cx=routed['operations']['cz']/abstract_cx,
                         event_groups=groups, detectors=per_detector))
    result = dict(scope='Exploratory replay and prior predictive check; no fitted decoder or new hardware job',
                  seed=seed, prior_simulation_shots_per_basis=shots, input_sha256=hashes, results=rows,
                  limitations=['Prior samples omit physical routing and device-specific noise.',
                               'Zero-frame comparison is not an unencoded-memory control.',
                               'Detector intervals are pointwise; detectors and strata are not independent.',
                               'These already-inspected hardware records are development data, not fresh validation.'])
    output.mkdir(parents=True, exist_ok=True)
    (output/'audit.json').write_text(json.dumps(result, indent=2), encoding='utf-8')
    import matplotlib
    matplotlib.use('Agg')
    import matplotlib.pyplot as plt
    fig, axes = plt.subplots(2, 1, figsize=(10, 6), sharex=True)
    for ax, row in zip(axes, rows):
        values = row['detectors']
        y = np.array([d['observed_fraction'] for d in values])
        ci = np.array([d['observed_ci'] for d in values])
        ax.errorbar(range(len(y)), y, yerr=[y-ci[:, 0], ci[:, 1]-y], fmt='o',
                    capsize=2, label='Physical QPU: 512 shots (pointwise 95% Wilson)')
        ax.plot([d['prior_fraction'] for d in values], 's--', label=f'Archived DEM prior: {shots:,} simulated shots')
        ax.set(ylabel=f'{row["basis"]}: firing fraction', ylim=(0, .8))
        ax.grid(alpha=.2)
        ax.legend(fontsize=8)
    axes[-1].set_xlabel('Stim detector index (not a raw measurement bit)')
    fig.suptitle('H1 prior predictive audit: assumed noise versus observed detector activity')
    fig.tight_layout()
    fig.savefig(output/'detector_activity.png', dpi=160)
    plt.close(fig)
    for row in rows:
        p = row['physical']
        print(f'{row["basis"]}: replay verified; helped={p["helped"]}, hurt={p["hurt"]}; '
              f'mean events physical={row["observed_mean_events"]:.3f}, prior={row["prior_mean_events"]:.3f}')
    print(f'Outputs: {output}')
    return result


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--source', type=Path, default=Path('reports/evidence/H1'))
    parser.add_argument('--output', type=Path, default=Path('results/h1-audit'))
    parser.add_argument('--shots', type=int, default=50000)
    parser.add_argument('--seed', type=int, default=20261107)
    args = parser.parse_args()
    audit(args.source, args.output, args.shots, args.seed)


if __name__ == '__main__':
    main()
