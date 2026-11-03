"""Independent Monte Carlo baseline replication through Sinter's own sampler.

Sampling seeds are managed internally by Sinter; this is not bitwise replay.
"""
import argparse
import json
from pathlib import Path
import sinter
import stim
from qec_project.statistics import exact_interval


def main():
    parser=argparse.ArgumentParser()
    parser.add_argument('point',type=Path)
    parser.add_argument('--shots',type=int,default=30000)
    args=parser.parse_args()
    if args.shots<1:parser.error('shots must be positive')
    circuit=stim.Circuit.from_file(args.point/'circuit.stim')
    task=sinter.Task(circuit=circuit,json_metadata=json.loads((args.point/'config.json').read_text()))
    stats=sinter.collect(num_workers=1,tasks=[task],decoders=['pymatching'],max_shots=args.shots,print_progress=False)
    result=[dict(shots=s.shots,failures=s.errors,discards=s.discards,seconds=s.seconds,
                 task_id=s.strong_id,ci=exact_interval(s.errors,s.shots),
                 sampling='Independent Sinter Monte Carlo; internal seed not user-controlled') for s in stats]
    (args.point/'sinter_independent.json').write_text(json.dumps(result,indent=2),encoding='utf-8')
    print(json.dumps(result,indent=2))


if __name__=='__main__':main()
