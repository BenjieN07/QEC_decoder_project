"""Score actual simulator outputs via the same downstream MWPM and truth samples."""
import argparse
import json
from pathlib import Path
import hashlib
import numpy as np
import pymatching
import stim
from qec_project.baseline import wilson


def main():
    parser=argparse.ArgumentParser()
    parser.add_argument('directory',type=Path)
    args=parser.parse_args();directory=args.directory
    meta=json.loads((directory/'metadata.json').read_text())
    point=Path(meta['replay'])
    dem=stim.DetectorErrorModel.from_file(point/'model.dem')
    if hashlib.sha256(str(dem).encode()).hexdigest()!=meta['dem_sha256']:
        raise RuntimeError('RTL/replay DEM mismatch')
    samples=np.load(point/'samples.npz')
    golden=np.load(point/'isolated.npz')
    residual=np.empty_like(samples['detectors']);frames=np.empty_like(samples['actual'])
    seen=set()
    for index,r,f in json.loads((directory/'observed_outputs.json').read_text()):
        shot=index-meta['sample_start']
        if 0<=shot<meta['sample_count']:
            if shot in seen:raise RuntimeError('duplicate RTL output')
            seen.add(shot)
            residual[shot]=[(r>>bit)&1 for bit in range(dem.num_detectors)]
            frames[shot]=[(f>>bit)&1 for bit in range(dem.num_observables)]
    if len(seen)!=len(samples['actual']):raise RuntimeError('missing sample outputs')
    if not np.array_equal(residual,golden['residual']) or not np.array_equal(frames,golden['frames']):
        raise RuntimeError('RTL/scalar/batch correction mismatch')
    prediction=pymatching.Matching.from_detector_error_model(dem).decode_batch(residual)^frames
    if not np.array_equal(prediction,golden['predicted']):raise RuntimeError('B/C predictions differ')
    failures=int(np.any(prediction!=samples['actual'],axis=1).sum())
    result=dict(shots=len(prediction),logical_failures=failures,ci=wilson(failures,len(prediction)),
                all_residuals_frames_and_predictions_match_B=True,graph=meta,
                scope='Actual RTL outputs followed by CPU MWPM; simulator wall time is not hardware latency')
    (directory/'end_to_end.json').write_text(json.dumps(result,indent=2),encoding='utf-8')
    print(f'RTL replay: {failures}/{len(prediction)} failures; all B/C predictions agree')


if __name__=='__main__':main()
