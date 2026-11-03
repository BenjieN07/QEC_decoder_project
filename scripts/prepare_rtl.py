"""Generate a fixed DEM graph implementation and independent golden vectors.

Run using the Windows project Python before running Linux verification.
"""
import argparse
import hashlib
import json
from pathlib import Path
import numpy as np
from qec_project.baseline import generate
from qec_project.config import load_config
from qec_project.predecoder import edges_from_dem, predecode
from qec_project.__main__ import git_info
import importlib.metadata
import platform
import stim


def pack(bits):
    return sum(int(value)<<index for index,value in enumerate(bits))


def prepare(basis, distance, output, replay=None):
    if replay is None:
        config = load_config('configs/smoke.json')
        config.update(basis=basis,distance=distance,rounds=distance)
        circuit = generate(config)
        sampled = circuit.compile_detector_sampler(seed=42).sample(1000)
    else:
        config = json.loads((replay/'config.json').read_text())
        basis,distance=config['basis'],config['distance']
        circuit=stim.Circuit.from_file(replay/'circuit.stim')
        sampled=np.load(replay/'samples.npz')['detectors']
    dem = circuit.detector_error_model(decompose_errors=True)
    edges = edges_from_dem(dem)
    n, observables = circuit.num_detectors,circuit.num_observables
    lines = [f'''// Generated from the saved DEM. Do not edit this generated file.
module local_predecoder (
 input wire clk, input wire rst,
 input wire in_valid, output wire in_ready,
 input wire [{n-1}:0] syndrome,
 output reg out_valid, input wire out_ready,
 output reg [{n-1}:0] residual,
 output reg [{observables-1}:0] frame
);
wire [{len(edges)-1}:0] active;
wire [{len(edges)-1}:0] chosen;
wire [{n-1}:0] next_residual;
wire [{observables-1}:0] next_frame;
assign in_ready = !out_valid || out_ready;
''']
    for index,(a,b,mask) in enumerate(edges):
        competitors = [f'active[{j}]' for j,(c,d,_) in enumerate(edges)
                       if j != index and (a in (c,d) or b in (c,d))]
        conflict = ' | '.join(competitors) or "1'b0"
        lines.append(f'assign active[{index}] = syndrome[{a}] & syndrome[{b}];')
        lines.append(f'assign chosen[{index}] = active[{index}] & ~({conflict});')
    for detector in range(n):
        choices = ' ^ '.join(f'chosen[{j}]' for j,(a,b,_) in enumerate(edges) if detector in (a,b)) or "1'b0"
        lines.append(f'assign next_residual[{detector}] = syndrome[{detector}] ^ ({choices});')
    for bit in range(observables):
        choices = ' ^ '.join(f'chosen[{j}]' for j,(_,_,mask) in enumerate(edges) if mask & (1<<bit)) or "1'b0"
        lines.append(f'assign next_frame[{bit}] = {choices};')
    lines.append('''always @(posedge clk) begin
 if (rst) begin
  out_valid <= 1'b0; residual <= 0; frame <= 0;
 end else if (in_ready) begin
  out_valid <= in_valid;
  if (in_valid) begin residual <= next_residual; frame <= next_frame; end
 end
end
endmodule
''')
    output.mkdir(parents=True,exist_ok=True)
    (output/'local_predecoder.sv').write_text('\n'.join(lines),encoding='utf-8')
    (output/'model.dem').write_text(str(dem),encoding='utf-8')
    rng = np.random.default_rng(912)
    vectors = [np.zeros(n,dtype=bool),np.ones(n,dtype=bool)]
    for a in range(n):
        s = np.zeros(n,dtype=bool); s[a] = True; vectors.append(s)
        for b in range(a+1,n):
            s = np.zeros(n,dtype=bool); s[[a,b]]=True; vectors.append(s)
    sample_start=len(vectors)
    vectors.extend(sampled)
    vectors.extend(rng.integers(0,2,size=(1000,n),dtype=np.uint8).astype(bool))
    rows = []
    for syndrome in vectors:
        residual,frame,_ = predecode(syndrome,edges,observables)
        rows.append([pack(syndrome),pack(residual),pack(frame)])
    (output/'vectors.json').write_text(json.dumps(rows),encoding='utf-8')
    (output/'metadata.json').write_text(json.dumps(dict(basis=basis,distance=distance,
        rounds=config['rounds'],detectors=n,observables=observables,edges=len(edges),vectors=len(rows),
        sample_start=sample_start,sample_count=len(sampled),replay=str(replay) if replay else None,
        config=config,git=git_info(),python=platform.python_version(),
        versions={name:importlib.metadata.version(name) for name in ('numpy','stim','pymatching')},
        dem_sha256=hashlib.sha256(str(dem).encode()).hexdigest()),indent=2),encoding='utf-8')
    print(output,len(rows),'vectors')


if __name__ == '__main__':
    parser = argparse.ArgumentParser()
    parser.add_argument('--basis',choices=['X','Z'],default='X')
    parser.add_argument('--distance',type=int,default=3)
    parser.add_argument('--output',type=Path,default=Path('results/rtl-x3'))
    parser.add_argument('--replay',type=Path,help='Use the exact circuit and saved shots from a study point')
    args = parser.parse_args()
    prepare(args.basis,args.distance,args.output,args.replay)
