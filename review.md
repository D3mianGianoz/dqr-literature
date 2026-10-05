# Related work: do anomaly detection methods suit automated sensor-data cleaning?

Status: **second tranche.** 344 papers inventoried, 11 read in depth.
Everything below distinguishes what was read from what was only title-triaged.

> **Correction.** An earlier version claimed none of the SoA's 49 references had a
> local PDF. That was a false negative: the inventory dropped the author segment
> from each filename, and the first matcher compared given names ("Hui") against
> titles instead of surnames ("Teh"). Both are fixed — `inventory.py` now keeps
> `author`, and `match_refs.py` matches on surname plus year. The true figure is
> **31 of 49 available locally**, including all seven citations carrying the
> section 2.4 argument. `soa_citations.csv` records the per-reference result.

## Why this question

The project is not about proposing a new anomaly detection algorithm. It asks
whether existing methods, applied to crane strain sensors, are fit for
**automated data cleaning** — automatically identifying faulty sensor data
before downstream structural analysis consumes it.

That reframing changes what "good" means. Precision matters more than recall: a
cleaner that flags good data as bad *destroys* it. The operating characteristic
that decides usability is the **false-alarm rate on clean data**, not detection
performance on faulty data.

## Corpus

`scripts/related_work/inventory.py` walks the literature root, parses year and
title from filenames, tags themes, and writes `inventory.csv` (344 rows, 131
untagged by filename alone). Re-run it as the collection grows.

| theme | papers |
|---|---|
| time-series anomaly detection | 125 |
| data quality / cleaning | 50 |
| sensor fault diagnosis | 36 |
| structural health monitoring | 20 |
| metrics / evaluation | 15 |
| benchmarking | 11 |
| model selection | 10 |
| drift / contamination | 10 |
| explainability | 9 |

## The SoA bibliography is a different literature

`20240606_D31_Damiano_v1.pdf` (USES2 deliverable D3.1, sensor data quality) has
**49 references spanning 1994–2024** — the data-quality foundations: Batini &
Scannapieca, Wang & Strong, Karkouch, Teh, Klein & Lehner, Naumann & Rolker,
Aggarwal, Chandola.

**31 of the 49 have a local PDF** (`soa_citations.csv`), so the SoA's
foundational citations can be read directly rather than trusted second-hand.
The 18 that cannot are the older data-quality canon and some IoT surveys.

The two corpora are not disjoint, they are differently weighted: the SoA is
built on **data-quality foundations** (Batini & Scannapieca, Wang & Strong,
Aggarwal, Chandola) while the collection is weighted toward **recent anomaly
detection and benchmarking**.

Locally available and load-bearing for the gap argument: Teh (2020), Karkouch
(2016), Nguyen (2023 survey), Wang (2019), Pang (2022), Haque (2024), Scholl
(2023), plus the algorithm primaries — Isolation Forest, EIF, HBOS, LOF, SVDD,
Keogh's SAX, LSTM, and Davis & Goadrich on precision-recall.

## Papers read in depth

### Bouman, Bukhsh & Heskes (2024) — *Unsupervised Anomaly Detection Algorithms on Real-world Data: How Many Do We Need?* (JMLR 25)

Largest comparison to date: 33 unsupervised AD algorithms on 52 real-world
multivariate **tabular** datasets. Findings:

- EIF (Extended Isolation Forest) outperforms most others overall.
- Two clear clusters emerge by anomaly locality: **"local"** anomalies sit in
  low-density regions *relative to nearby samples*; **"global"** anomalies sit in
  overall low-density regions.
- **kNN wins on local data sets.**

Directly relevant: strain spikes are prototypically *local* anomalies, and kNN
is one of the two criteria in the blind pipeline. The paper's result is on
tabular data, not time series, so transfer to strain is an open question this
project can address rather than assume.

### Chavelli, Boniol & Thomazo (2025) — *Toward Interpretable Evaluation Measures for Time Series Segmentation* (arXiv:2510.23261)

Argues existing evaluation is critically limited: measures focus on change-point
accuracy or use point-based measures such as Adjusted Rand Index, which "fail to
capture the quality of the detected segments, ignore the nature of errors, and
offer limited interpretability." Introduces:

- **WARI** (Weighted Adjusted Rand Index) — accounts for the position of
  segmentation errors.
- **SMS** (State Matching Score) — identifies and scores **four fundamental
  types of segmentation error**, with error-specific weighting, and exposes
  error provenance.

Relevant because the blind pipeline does not emit point flags; it emits
**episodes** (contiguous groups of flagged points). Boundary quality and error
type are therefore first-class, and point-based metrics would mis-measure them.

### Sørbø & Ruocco (2024) — *Navigating the Metric Maze: A Taxonomy of Evaluation Metrics for Anomaly Detection*

Twenty metrics analysed against a taxonomy of *how they are calculated*, plus a
property set and case studies. Core claim: "limited agreement on which metrics
are best suited for specific scenarios and domains," and the most commonly used
metrics "have faced criticism in the literature." Conclusion: **metric choice
must be made with care, per task.**

### Röchner et al. (2025) — *We Need to Rethink Benchmarking in Anomaly Detection* (position paper)

Argues AD progress has stagnated because of **how we evaluate**, not because of
a lack of algorithms — differences between established baselines and new methods
are minor. Three required improvements:

1. Identify AD scenarios from a **common taxonomy**.
2. Analyse pipelines **end-to-end and by component**.
3. Evaluate meaningfully **with respect to the scenario's objectives**.

This paper essentially argues for the study being proposed here: component-wise
analysis against a use-case objective, not a leaderboard.

### Adaptive fault diagnosis for simultaneous sensor faults in SHM (2023)

Notes that **most fault-diagnosis concepts for SHM assume single-fault
occurrence**, which "may oversimplify actual fault occurrences in real-world SHM
systems." The approach uses **analytical redundancy** — correlated data from
multiple sensors — with ANN models exploiting inter-sensor correlation.

This is the established SHM methodology for separating sensor faults from real
structural behaviour, and it is what the project needs in order to use its ten
available strain gauges rather than one.

### Bagnall et al. / Bake Off Redux (2024)

The 2017 "bake off" compared 18 time-series classification algorithms on 85
UCR datasets and found only **nine performed significantly better than the DTW
and Rotation Forest benchmarks**. Redux re-runs the comparison against 112
datasets and newer algorithms. The transferable lesson is that a large body of
proposed algorithms does not beat simple baselines — the presumption that
better methods are available is itself worth testing.

### Choose Wisely: model selection for anomaly detection (2023)

States plainly that benchmark studies show **"no overall best anomaly detection
methods exist when applied to very heterogeneous time series datasets."**
Concludes the only viable approach over heterogeneous data is *model selection
based on the characteristics of each series*.

### Donné & Davis (2026) — Robust anomaly detection under contaminated data

In semi-supervised AD, models are trained on data assumed to represent normal
behaviour. In practice that "normal" set contains an **unknown fraction of
abnormal or degraded samples**, which harms diagnostic performance.

Directly relevant: the pipeline trains its KNN criterion on a "healthy anchor"
parquet. If that anchor is contaminated, the detector is degraded in an
unmeasurable way. This is a caveat on current results *and* a candidate
follow-up.

### Zhang, Ding, Du, Xia & Wang (2022) — Sensor faults and extreme events, SVDD

SHM framing that makes the distinction explicit: **sensor faults reduce
measurement fidelity, while extreme events threaten the monitored structure.**
Both corrupt the same signals, and separating them is the core SHM problem.

## What this means for the study

The literature converges on four requirements that map directly onto the current
blind pipeline:

| literature requirement | source | status in our system |
|---|---|---|
| metric matched to task, not defaults | Sørbø & Ruocco 2024 | point metrics would mis-measure episodes |
| segment-aware error types | Chavelli et al. 2025 | episodes emitted, no segment metric |
| component-wise pipeline analysis | Röchner et al. 2025 | scoring/thresholding/grouping conflated |
| analytical redundancy over multiple sensors | SHM FD 2023 | 1 of 10 strain gauges used |
| assume training data is clean | Donné & Davis 2026 | healthy anchor never checked for contamination |
| expect new algorithms to beat simple baselines | Bake Off Redux 2024 | untested here; ROC and KNN have no simple baseline |

And one open transfer question:

- AD results established on **tabular** data (Bouman et al. 2024) are assumed
  to transfer to **time-series strain**. That assumption is untested here and
  cheap to test.

### Teh, Kempa-Liehr & Wang (2020) — Sensor data quality: a systematic review

The systematic review the thesis is built on. 6970 records screened, **57
selected**. Frames four questions: what types of physical sensor errors exist,
how to quantify or detect them, how to correct them, and in which domains.
Findings: the error types addressed are **mostly missing data and faults such
as outliers, bias and drift**, and the most common detection solutions are
**PCA and artificial neural networks**.

That error taxonomy is nearly identical to `docs/disturbance_vocabulary.md`,
which is reassuring for its stability. PCA being the dominant approach is worth
noting, since `docs/overlap.md` deferred it.

### Scholl, Spiegler et al. (2023) — Integrated framework for data quality fusion

Proposes fusing sensor data streams and their associated data-quality attributes
into **a single interpretable value** representing current data quality, using
maximum-likelihood and fuzzy-logic fusion of domain knowledge with sensor
measurements. This is the "DQ dimensions" approach the thesis cites.

## Your own prior framing

Two documents in `Foundations/` state the position more sharply than this file
did, and are worth reading before the paper is drafted.

**`20250514_Open_research_question.docx`**

> "How can more diverse, representative and labeled real-world datasets for
> sensor fault detection be created and utilized?"

with the intended contribution being *the creation and public release of a
high-quality, labeled real-world dataset from the company's domain*, following
Nguyen et al. (marine) and Attarha et al. Two supporting statements matter for
this project:

- "faulty sensor data [...] can mimic normal behaviour" (AssureSense, 2024)
- "normal operational variability can be mistaken for anomalous" (Attarha, 2023)

The second is exactly the distinction the withdrawn `operational` category was
trying to capture — and the literature treats it as a *known failure mode of
detectors*, not a gap.

**`20250318_Gaps#2.docx`** — monitoring-context gaps:

1. **High anomaly ratios.** Nguyen et al. (2024) note most AD is developed on
   data with an anomaly ratio below 1%. Crane strain data is not in that regime.
2. **Real-time adaptation and fault *management***, not only detection.
3. **Subtle and mimicking faults.**
4. **Short training phases** for scalable deployment.
5. **Context-independent aims are the wrong target.** Citing Keogh: *"doing
   well on one of the public datasets is a sufficient condition to declare an
   anomaly detection algorithm useful."*

Point 5 is the field-level critique that your stated contribution answers.

## Not yet ingested

- 336 of 344 papers are title-triaged only.
- The 2025-2026 metrics cluster (VUS, segmentation measures) is only partly read.
- The seven section-2.4 citations behind the gap argument are not locally
  available and have not been read in full.
- The `20240606_D31_Damiano_v1.pdf` thesis draft has not been read in this repo.
- `gianotti_et_al._2026_assessing_reliability_of_cm_scale_optical_fiber_strain_sensing`
  is adjacent work that has not been reviewed.

Next tranche should prioritise: the remaining metrics papers, model-selection
studies, and the data-quality/cleaning cluster, since that is the application
side of the bridge.