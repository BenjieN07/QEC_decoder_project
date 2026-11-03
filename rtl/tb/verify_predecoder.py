"""Cycle scoreboard: simultaneous traffic, stalls, bubbles and in-flight reset."""
import json
import os
from pathlib import Path
import random
import cocotb
from cocotb.triggers import Timer


@cocotb.test()
async def verify(dut):
    vectors = json.loads(Path(os.environ['VECTOR_FILE']).read_text())
    rng = random.Random(19)
    pending = None
    index = 0
    consumed = 0
    cycles = 0
    resets = 0
    held_valid = False
    observed = []
    while index < len(vectors) or pending is not None:
        dut.clk.value = 0
        reset = cycles == 0 or cycles in (35,220)
        ready = cycles < 25 or rng.random() < .7
        valid = index < len(vectors) and (held_valid or cycles < 25 or rng.random() < .85)
        dut.rst.value = int(reset)
        dut.out_ready.value = int(ready)
        dut.in_valid.value = int(valid)
        dut.syndrome.value = vectors[index][0] if valid else 0
        await Timer(5,unit='ns')
        assert int(dut.out_valid.value) == int(pending is not None)
        if pending is not None:
            assert int(dut.residual.value) == pending[1]
            assert int(dut.frame.value) == pending[2]
        in_ready = int(dut.in_ready.value)
        held_valid = bool(valid and not in_ready and not reset)
        if reset:
            pending = None
            resets += 1
        else:
            if pending is not None and ready:
                consumed += 1
                observed.append([pending_index,int(dut.residual.value),int(dut.frame.value)])
                pending = None
            if valid and in_ready:
                pending = vectors[index]
                pending_index=index
                index += 1
        dut.clk.value = 1
        await Timer(5,unit='ns')
        cycles += 1
        assert cycles < len(vectors)*10
    Path(os.environ['CYCLE_FILE']).write_text(json.dumps(dict(
        vectors_accepted=index,outputs_consumed=consumed,cycles=cycles,resets=resets,
        note='Resets discard pending output; 10 ns test clock is not achieved timing',
        unstalled_latency_cycles=1,unstalled_initiation_interval_cycles=1),indent=2))
    Path(os.environ['OUTPUT_FILE']).write_text(json.dumps(observed))
