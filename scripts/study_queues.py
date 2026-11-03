"""Compare A/B and explicitly hypothetical C using measured per-window services."""
import argparse
import json
from pathlib import Path
import numpy as np
from qec_project.queueing import replay
from qec_project.encoding import encode


def main():
    parser=argparse.ArgumentParser();parser.add_argument('study',type=Path)
    args=parser.parse_args();output=args.study
    spec=json.loads((output/'manifest.json').read_text())['study']
    summaries=[]
    for point in sorted(output.glob('point-*')):
        config=json.loads((point/'config.json').read_text())
        original=np.load(point/'samples.npz')['detectors']
        for mode in ('isolated','max2'):
            timing_file=point/f'{mode}-timing.npz'
            if not timing_file.exists():continue
            stages=np.load(timing_file)['stages_ns'];count=len(stages)
            hybrid=np.load(point/f'{mode}.npz')
            zeros=np.zeros(hybrid['frames'].shape[1],dtype=bool)
            bytes_a=np.array([len(encode(s,zeros)) for s in original[:count]])
            bytes_b=hybrid['sparse_bytes'][:count]
            for period in spec['arrival_periods_ns']:
                for bandwidth in spec['bandwidths_bits_per_second']:
                    for architecture in ('A','B','C_assumed'):
                        if architecture=='A':services=np.column_stack([stages[:,0],bytes_a*8e9/bandwidth,stages[:,1]])
                        elif architecture=='B':services=np.column_stack([stages[:,2]+stages[:,3],bytes_b*8e9/bandwidth,stages[:,4]])
                        else:
                            # C has only been simulated for the unrestricted rule on selected graphs.
                            if mode!='isolated':continue
                            services=np.column_stack([spec['rtl_clock_period_ns_assumed']+stages[:,3],bytes_b*8e9/bandwidth,stages[:,4]])
                        result=replay(services,period,config['rounds'],spec['deadline_ns'],spec['queue_capacity_windows'])
                        records=result.pop('records')
                        result.update(point=point.name,architecture=architecture,mode=mode,basis=config['basis'],
                                      distance=config['distance'],rounds=config['rounds'],p=config['noise']['after_clifford_depolarization'],
                                      arrival_period_ns=period,bandwidth_bits_per_second=bandwidth,
                                      C_warning='Clock period assumed, serialization and downstream CPU measured; no target timing closure' if architecture=='C_assumed' else None)
                        summaries.append(result)
                        if point.name=='point-01' and mode=='isolated' and bandwidth==spec['bandwidths_bits_per_second'][-1] and period==spec['arrival_periods_ns'][0]:
                            (output/f'queue_trace_{architecture}.json').write_text(json.dumps(records),encoding='utf-8')
    (output/'queue_summary.json').write_text(json.dumps(summaries,indent=2),encoding='utf-8')
    import matplotlib
    matplotlib.use('Agg')
    import matplotlib.pyplot as plt
    fig,ax=plt.subplots()
    for path in sorted(output.glob('queue_trace_*.json')):
        records=json.loads(path.read_text())
        ax.plot([r['window_id'] for r in records],[r['feedback_ns']/1000 for r in records],label=path.stem.replace('queue_trace_',''))
    ax.set(xlabel='Independent complete memory window',ylabel='Modeled feedback latency (us)',
           title='X d=3, p=.005; hypothetical 1 us/round, 1 Gbit/s')
    ax.legend();fig.tight_layout();fig.savefig(output/'figures/queues.png',dpi=160);plt.close(fig)
    print('Queue scenarios:',len(summaries))


if __name__=='__main__':main()
