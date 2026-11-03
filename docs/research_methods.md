# Controlled comparison methods

The study's JSON config defines the Cartesian grid, sampling seed, trials,
timing subset, arrival periods and bandwidth assumptions. Per-point seeds differ
by a fixed increment. Each point saves its exact circuit, DEM, config, samples,
true observables and A/B predictions. Comparing A/B always uses identical shots.
Stim samples may vary across versions/platforms; saved sample replay is the
stronger control. This is a noisy rotated surface-code memory study, not logical
gates or threshold estimation. All four circuit noise channels equal p.

The two modes are isolated admissible pairs, and the same rule restricted to
windows with at most two events. Higher-event windows in the second mode fall
back entirely to MWPM. Both use original-syndrome exclusivity. Neither is a proof
that the physical error chosen was correct. Boundary and correlated local guesses
are excluded, not removed from the downstream error model.

Batch preprocessing is a chunked NumPy execution of the scalar golden rule.
Accuracy is checked on all shots; real-sample scalar equivalence is checked on
100 per point and randomized multi-observable tests. Predecoder changes can
change logical accuracy; it is never assumed equal to MWPM.

Wilson 95% intervals describe failure probability per complete memory window.
Zero-failure points also include a two-sided exact binomial upper bound. Paired
rate-change intervals use 97.5% Clopper–Pearson intervals for each discordant
category and subtract the endpoints: Bonferroni guarantees at least 95% coverage
for their difference. This is conservative but remains nonzero when there are no
disagreements. Intervals are pointwise; the grid is exploratory and no adjustment
for multiple hypothesis searches is claimed. Equal observed failures is not an
equivalence test or a prespecified acceptable accuracy margin.

Wire records use a 16-byte header plus actual detector bytes and byte-rounded
logical frame. Baseline frames are zero but have the same allocated field. Sparse
indices are little-endian uint32, dense data is bit-packed, and adaptive data adds
one explicit format byte to the shorter record. Dimensions/schema are negotiated
once out of band; physical link framing, CRC and protocol overhead are not modeled.
The study constructs sparse/dense byte objects; adaptive byte counts add the
tested one-byte tag to their minimum. Actual payload serialization has roundtrip tests.

Warmup precedes timing on a fixed subset. Five trials alternate A/B order.
Batch timings are nanoseconds/window after amortization, including the NumPy
predecoder's allocations but excluding setup, sampling, serialization and I/O.
Per-window end-to-end classical timing separately includes scalar predecode,
serialization and MWPM, excluding quantum sampling and physical transport. Tail
percentiles on 1000 windows have limited precision; five batch trials do not
establish reliable p99 batch variability. Raw trial times and separate scopes are
saved. Array bytes and process CPU time are recorded; array bytes are not RSS.
The laptop is shared, unpinned and not a controlled hardware performance platform.

The final evidence replaces initial timings with a separate sequential replay after
sampling and hardware builds stop. Its revision is recorded separately in the
manifest. Stage-level scalar timings include timer overhead. The queue replay uses
these measured stage distributions in original shot order, one window per rounds
arrival periods, with independent pipelined front-end, transfer and MWPM resources.
Capacity includes each stage's in-service window. Simulated unlimited queues retain
all work; exceeding configured capacity is reported as an infeasible finite-buffer
schedule, not hidden drops. Window-fill time is included; terminal-measurement
overhead beyond the supplied window interval is assumed zero.

For C, only selected fixed graphs are functionally simulated. The extrapolated
C_assumed queue rows replace preprocessing with an assumed 10 ns and retain
measured CPU serialization/downstream services. These scenarios do not establish
that any RTL graph can meet that clock, nor that the extrapolated graphs were
verified. They are a sensitivity model and cannot be called measured speedups.

RTL results are equivalent-function simulation for fixed graphs, not physical
FPGA runs. One unstalled cycle is an architectural count. An assumed 10 ns period
in queue scenarios is hypothetical and has not passed timing closure. Generic
Yosys cell/register counts are technology-independent estimates. Any hardware
arrival/transfer comparison must retain this distinction.
