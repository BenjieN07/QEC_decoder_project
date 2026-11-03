"""Replay timing sequentially after sampling/generation/build work has stopped."""
import argparse
import json
from pathlib import Path
from time import perf_counter_ns
import numpy as np
import pymatching
import stim
from qec_project.encoding import encode
from qec_project.predecoder import predecode,predecode_batch,edges_from_dem
from qec_project.research import timing,describe_ns
from qec_project.research import write_csv
from qec_project.__main__ import git_info
from datetime import datetime,timezone


def main():
    parser=argparse.ArgumentParser();parser.add_argument('study',type=Path)
    args=parser.parse_args();output=args.study
    manifest=json.loads((output/'manifest.json').read_text());spec=manifest['study']
    rows=json.loads((output/'study.json').read_text())
    manifest['retiming']={'git':git_info(),'status':'running','started_utc':datetime.now(timezone.utc).isoformat(),
                         'scope':'Sequential replay after study sampling and RTL builds; shared laptop remains unisolated'}
    (output/'manifest.json').write_text(json.dumps(manifest,indent=2),encoding='utf-8')
    for point in sorted(output.glob('point-*')):
        config=json.loads((point/'config.json').read_text())
        samples=np.load(point/'samples.npz');detectors=samples['detectors']
        dem=stim.DetectorErrorModel.from_file(point/'model.dem')
        matching=pymatching.Matching.from_detector_error_model(dem);edges=edges_from_dem(dem)
        zeros=np.zeros(dem.num_observables,dtype=bool)
        selected=[r for r in rows if r['seed']==config['seed']]
        for row in selected:
            limit=None if row['mode']=='isolated' else int(row['mode'][3:])
            small=detectors[:min(len(detectors),spec['timing_shots'])];count=len(small)
            warm,_=predecode_batch(small,edges,dem.num_observables,limit)
            matching.decode_batch(small);matching.decode_batch(warm)
            trials=[]
            for trial in range(spec['timing_trials']):
                if trial%2==0:_,a_ns=timing(lambda:matching.decode_batch(small))
                (r,f),pre_ns=timing(lambda:predecode_batch(small,edges,dem.num_observables,limit))
                _,decode_ns=timing(lambda:matching.decode_batch(r)^f)
                if trial%2:_,a_ns=timing(lambda:matching.decode_batch(small))
                trials.append(dict(baseline_ns=a_ns/count,predecode_ns=pre_ns/count,residual_decode_ns=decode_ns/count,total_hybrid_ns=(pre_ns+decode_ns)/count))
            singles=[];stages=[]
            for index,s in enumerate(detectors[:min(len(detectors),spec['single_shots'])]):
                def a():
                    start=perf_counter_ns();encode(s,zeros,index,config['rounds']-1,True)
                    middle=perf_counter_ns();matching.decode(s)
                    end=perf_counter_ns();return [middle-start,end-middle]
                def b():
                    start=perf_counter_ns()
                    r,f,_=predecode(s,edges,dem.num_observables) if limit is None or s.sum()<=limit else (s,zeros,[])
                    pre=perf_counter_ns();encode(r,f,index,config['rounds']-1,True)
                    encoded=perf_counter_ns();matching.decode(r)^f
                    end=perf_counter_ns();return [pre-start,encoded-pre,end-encoded]
                if index%2==0:a_stage,a_total=timing(a);b_stage,b_total=timing(b)
                else:b_stage,b_total=timing(b);a_stage,a_total=timing(a)
                singles.append([a_total,b_total]);stages.append(a_stage+b_stage)
            row['trials']=trials
            row['batch_per_window_ns']={key:describe_ns([trial[key] for trial in trials]) for key in trials[0]}
            row['single_window_ns']={'A':describe_ns(np.array(singles)[:,0]),'B_scalar':describe_ns(np.array(singles)[:,1])}
            row['retimed_sequentially']=True
            np.savez_compressed(point/f'{row["mode"]}-timing.npz',single_timing_ns=np.array(singles),
                                stages_ns=np.array(stages),stage_names=['A_serialize','A_decode','B_predecode','B_serialize','B_decode'])
            (point/f'{row["mode"]}.json').write_text(json.dumps(row,indent=2),encoding='utf-8')
        (output/'study.json').write_text(json.dumps(rows,indent=2),encoding='utf-8')
        print('Retimed',point.name,flush=True)
    from qec_project.research_plots import plots
    write_csv(rows,output)
    plots(output)
    manifest['retiming'].update(status='complete',finished_utc=datetime.now(timezone.utc).isoformat())
    (output/'manifest.json').write_text(json.dumps(manifest,indent=2),encoding='utf-8')


if __name__=='__main__':main()
