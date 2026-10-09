# De Bruijn, Meratnia, et al. (2016) — Benchmark datasets for fault detection and classification in sensor data

The precedent behind the open research question. States that although
algorithmic solutions are proposed, **"the field lacks a set of benchmark sensor
datasets,"** and defines what one must satisfy:

- **(a)** based on **real-world raw sensor data** from various sensor deployments;
- **(b)** contains **natural *or* artificially injected** faulty data reflecting
  various deployment problems, **including missing data points**;
- **(c)** **all data points annotated with ground truth** — whether accurate,
  and if faulty, the type.

They publish three such datasets totalling **5,783,504 points** across 10 Intel
Lab, 16 Smart Santander and SensorScope sensors, with fault types *random,
malfunction, bias, drift, polynomial drift* and combinations.

Three consequences for this project:

1. Criterion (b) admits **natural** faults. Declining fault injection does not
   disqualify a dataset from being a benchmark.
2. Criterion (c) asks whether data is *accurate* and what *data* fault it is —
   not what physically broke the gauge. Stale, missing and out-of-range data
   are annotatable without a maintenance record. That is a materially weaker
   claim than fault diagnosis, and it is available here.
3. **Scale.** 5.78M points across three datasets; the current run scores
   9.6M rows over ten gauges. The dataset is already benchmark-scale by these
   criteria.
