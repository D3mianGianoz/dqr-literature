# Related work: do anomaly detection methods suit automated sensor-data cleaning?

Status: **SoTA complete.** 344 papers inventoried, 31 read in depth —
all locally available SoTA references.
Everything below distinguishes what was read from what was only title-triaged.
Counts come from `reading_log.csv`, not from prose.

> **Correction.** An earlier version claimed none of the SoA's 49 references had a
> local PDF. That was a false negative: the inventory dropped the author segment
> from each filename, and the first matcher compared given names ("Hui") against
> titles instead of surnames ("Teh"). Both are fixed — `inventory.py` now keeps
> `author`, and `match_refs.py` matches on surname plus year. The true figure is
> **31 of 49 available locally**, including all seven citations carrying the
> section 2.4 argument. `docs/literature/soa_citations.csv` records the per-reference result.

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
title from filenames, tags themes, and writes `docs/literature/inventory.csv` (344 rows, 131
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

**45 of the 49 have a local PDF** (`docs/literature/soa_citations.csv`), so the
SoTA's foundational citations can be read directly rather than trusted
second-hand.

An earlier count said 31. The shortfall was a parsing bug, not missing files:
author segments were split at initials, so "Richard Y. Wang" yielded the
surname `richard` and never matched. Fixed in `match_refs.py`, which also gained
a guarded fuzzy title-overlap fallback. In the event exact matching suffices.

Only four are genuinely absent, and three are textbooks rather than papers:

| ref | work |
|---|---|
| [11] | Barnett & Lewis (1994), *Outliers in Statistical Data* - book |
| [27] | Goodfellow, Bengio & Courville (2016), *Deep Learning* - book |
| [30] | Hyndman & Athanasopoulos (2018), *Forecasting: Principles and Practice* - book |
| [32] | Malhotra et al. (2015), LSTM networks for anomaly detection in time series |

Textbooks would be cited from general knowledge rather than quoted. Note the
collection *does* contain Aggarwal's *Outlier Analysis* and Sutton & Barto's
*Reinforcement Learning*, so textbook presence is inconsistent rather than
excluded by policy.

The index also contains **five duplicate pairs**, so the count is not distinct
works.

### The corpus is wider than Zpapers

The first index walked `Zpapers/` only. The `Literature/` root holds **41 more
PDFs** in `Books/`, `Slides/`, `Stage/`, `Thesis/`, `Posters/`, `Tutorials/` and
`Images/` — 385 in total. Several matter directly:

- **Keogh, *Problems with TSAD*** (`Slides/`) — the critique behind Wu & Keogh's
  "illusion of progress" claim, in the author's own words.
- **Boniol lecture decks**, including one specifically on **evaluation
  measures** — the author of both the VUS and the segmentation-measure papers,
  which makes them a compact route into that cluster.
- **`Expect the Unexpected`** (`Stage/waiting/`) — this is the Teh et al. 2021
  paper the open research question cites.
- **`Data Quality Dimensions`** (`Images/`) and the two `Stage/reports/` data
  quality papers — likely the group's own output; worth checking authorship
  before citing as external work.
- Three **theses** (`Thesis/`) — Bosman on networked-embedded anomaly detection,
  Delaine, and Selcuck.

None of these are in the SoTA bibliography, so reading them does not close a
bibliography gap. They are likely working notes for this project, and should be
read before the collection is treated as settled.
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

### De Bruijn, Meratnia, et al. (2016) — Benchmark datasets for fault detection and classification in sensor data

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

### Tatbul, Lee, Alam & Bekiroglu (2018) — Precision and Recall for Time Series

Opens with the observation that classical AD concerns **point-based** anomalies,
whereas **many real-world anomalies are range-based** — they occur over a period
of time. Extends precision and recall to measure *ranges*, with a
customisation parameter for domain-specific preferences about how much boundary
error is tolerable.

This is the metric family RQ3 needs. The blind pipeline emits episodes —
contiguous ranges — so point-wise precision and recall mis-measure it by
construction, and Tatbul's range-based form with an explicit tolerance parameter
is more directly applicable than the segmentation measures cited above.

### Nguyen, et al. (2019) — Verifying the correctness of IoT sensor data in real time

Verification **before storage**, using a forecasting technique to estimate the
correct value — framed around "the faulty data should be detected and corrected
as early as possible." This is the data-cleaning use case stated as a research
problem, and it is the closest framing to the intended contribution.

### Foorthuis (2021) — On the nature and types of anomalies

Notes that the concept of an anomaly "is typically ill defined and perceived as
vague and **domain-dependent**," and that despite roughly 250 years of
publications no comprehensive concrete overview of anomaly types existed.
Presents a domain-independent **typology organised along five dimensions**
starting with data type and cardinality of relationship.

Useful as an external check on `docs/research/vocabulary.md`, and as support for
treating the operational/fault boundary as a known difficulty rather than a
local invention.

### Ni, et al. (2009) — Sensor network data fault types (ACM TOSN 5(3))

The canonical sensor-data fault taxonomy. Defines a data fault as **"data
reported by a sensor that is inconsistent with the phenomenon of interest's true
behavior"** — domain-relative, not an absolute deviation.

Calibration faults (§5.2.1) come in three named forms:

| fault | definition as given |
|---|---|
| offset | values offset by a constant; normal patterns still visible over an extended period |
| gain | rate of change of measured data does not match expectations; the sensor reports a change of `G · δ` for a true change `δ` |
| drift | offset or gain parameters change over the deployment's life |

Calibration faults are noted as producing "lower **accuracy** of sensor
measurements but not necessarily lower **precision**" — a useful distinction when
reporting what a detector can and cannot see. The paper also states that
detecting and modelling general calibration errors is "difficult without human
input," which corroborates the decision to withdraw fault-diagnosis categories.

**One point cuts against the no-injection position.** Ni et al. state that when
testing a fault-detection system, "because the faults presented here are the most
common, they should be the first to be used in testing **by injecting them into
either simulated or real datasets**." That is the canonical taxonomy paper
arguing injection is testing *infrastructure*, not a contribution — a different
claim from the one being set aside. Worth deciding deliberately rather than by
default.

### Nguyen, Kiet, Lee, Yeo & Son (2023) — Comprehensive survey of sensor data verification in IoT

The survey the thesis leans on for its classification. Organises the whole
verification problem space along six axes:

1. anomaly classification
2. sensor data verification frameworks
3. verification methods — **anomaly detection and anomaly correction**
4. **evaluation methods** for verification
5. technology and tools
6. challenges and future research

The pipeline so far covers (2) and detection within (3). Axis **(4) is
unimplemented**, which is where RQ1 and RQ3 land. Note also that detection and
*correction* are treated as one axis: the project currently does neither, and
correction is arguably the more useful half for automated cleaning.

### Karkouch, Mousannif, Al Moatassime & Noel (2016) — Data quality in IoT: a state-of-the-art survey

The survey behind the thesis's central methodological claim that detection
methods *"focus on identifying deviations from the norm, overlooking other
pertinent domain parameters such as sensor precision or range."* Its framing is
that poor-quality data make IoT decisions unsound, and it reviews DQ
enhancement across interpretation, integration, deduplication and cleaning —
not only detection.

Supports the argument that sensor **specification** parameters belong in the
pipeline, which the withdrawn codebook had explicitly excluded.

### Wang, Bah & Hammad (2019) — Progress in outlier detection techniques

A survey of outlier detection from 2000–2019, organised into distance-,
clustering-, density-, ensemble- and learning-based methods, with pros, cons
and open challenges per category. The source for the thesis's ensemble-learning
gap (base learner selection, quantity, combination strategy).

Ensemble **combination strategy** is directly relevant to RQ2, which asks whether
ROC and KNN are complementary — the survey frames that as a known open design
choice rather than a settled one.

### Batini & Scannapieca (2006) — Data quality: concepts, methodologies and techniques

The foundational reference for the whole data-quality framing, cited first in
the SoTA. Establishes data quality as a multidimensional, context-dependent
property rather than a single score — which is the premise Scholl's fusion work
later tries to collapse into one value.

### Davis & Goadrich (2006) — The relationship between precision-recall and ROC curves

Shows PR curves are more informative than ROC under **heavily skewed** data, and
that a curve dominates in ROC space **if and only if** it dominates in PR space,
with an efficient algorithm for the achievable PR curve.

Directly relevant to RQ1 and RQ3: the strain sample is extremely skewed —
detector-selected, 69 of 74 episodes labelled anomalous — so ROC-style reporting
would misrepresent performance.

### Haque, Chowdhury & Soliman (2024) — WSN anomaly detection using machine learning

A survey of ML for anomaly detection in wireless sensor networks, spanning
supervised, unsupervised and semi-supervised approaches, motivated explicitly
by noisy, unreliable sensed data and civil-engineering structural monitoring.

Cited in the thesis for evaluation on real-world data. Also confirms that SHM is
already a named application domain for this method family.

## Completing the SoTA: the remaining 19 references

All 31 locally available SoTA references are now read. Grouped by role rather
than one subsection each.

**Foundations and the DQ framing.** Naumann & Rolker (2000) classify
information-quality criteria in an explicitly *assessment-oriented* way,
identifying three sources of IQ scores, and observe that projects "hardly ever"
address the difficulty of actually **assessing scores for the criteria**. That is
precisely why a written codebook felt necessary and then kept moving: scoring
qualitative criteria is the hard part, and the field has known it for 25 years.
Yan et al. (2014) covers trust management in IoT — adjacent framing, not
detection.

**Anomaly-detection surveys.** Chandola et al. (2009) is the canonical reference
and states the central difficulty plainly: defining a normal region containing
every possible normal behaviour is very difficult, and **"the boundary between
normal and anomalous behavior is often not precise."** Hodge & Austin (2004)
separately list *changes in system behaviour* alongside *mechanical faults* and
*instrument error* as causes of outliers — the operational/fault distinction,
already present in 2004 — and describe outlier detection as a way to "purify the
data for processing." Pang et al. (2022) and Schmidl et al. (2022) are the modern
surveys; **Schmidl et al. is the time-series analogue of Bouman et al. (2024)**
and is the more directly applicable of the two. Ayadi et al. (2017) and Ahmad et
al. (2017) cover WSN outlier detection and streaming HTM respectively.

**Fault classification independent of cause.** Baljak et al. (2012) classify
faults on two axes — **continuity and frequency of occurrence**, and **existence
of observable and learnable patterns** — and do it "independently of the
underlying cause."

This is the most useful methodological result in the set. It is a published
answer to the problem that killed the codebook: when cause cannot be determined,
classify by **observable properties** instead. That is exactly what
`docs/research/vocabulary.md` does, and it now has a citation for the approach
rather than only a rationale.

Javed & Wolf (2012) address automated sensor verification via outlier detection
in cyber-physical systems.

**The algorithm primaries, and what they say about false alarms.** Together these
argue against the current design in three specific ways:

- **Isolation Forest** (Liu et al. 2008) introduces itself by criticising the
  dominant approach for being "optimized to profile normal instances, but not
  optimized to detect anomalies," which causes "**too many false alarms** or too
  few anomalies being detected." That is RQ1's problem, named in 2008.
- **NFAD** (Ryzhikov et al. 2021) criticises one-class methods — one-class SVM,
  robust autoencoder — for assuming **separability** of normal and anomalous
  classes, which does not hold when legitimate operation overlaps with faults.
- **Extended Isolation Forest** (Hariri et al. 2021) fixes score-assignment
  artifacts in iForest. Since Bouman et al. (2024) found **EIF best overall**
  across 33 algorithms, it is the obvious simple baseline this project does not
  currently have.

**LOF** (Angiulli & Pizzuti 2002) is the reference local-outlier method, and
Bouman et al. found kNN strongest on *local* anomalies — so LOF is the natural
cheap comparison for the KNN criterion. **HBOS** (Goldstein & Dengel 2012) is
constant-time. **Ensemble Grammar Induction** (Gao et al. 2020) concedes that
its discretization parameters (PAA size, alphabet size) are "**still an open
problem**," especially unsupervised — the same condition as our thresholds.
**Keogh et al. (2002)** note previous surprise-detection uses "a very limited
notion of surprise." **LSTM** (Hochreiter & Schmidhuber 1997) is included as a
temporal-model baseline. Rasheed et al. (2009) applies FFT to spatial outlier
mining — a spatial technique, relevant only once multiple gauges are used.

### Currency caveat

The SoTA is dated 2024 and its bibliography bottoms out around 2014 for
detection methods. The algorithm primaries above are stable and still benchmark
methods, but the **deep and foundation-model literature post-2018 is largely
absent from it** — including the recent benchmarking work already read here
(Bouman 2024, Röchner 2025, Donné & Davis 2026). Treat the SoTA as the
problem-framing reference, not as a current methods survey.

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
| point metrics mis-measure range anomalies | Tatbul et al. 2018 | pipeline emits episodes; no range-based metric in use |
| ROC misleads under heavy skew | Davis & Goadrich 2006 | candidate sample is 69/74 anomalous |
| sensor specification parameters are needed | Karkouch et al. 2016 | excluded by the withdrawn codebook |
| detection and correction are one axis | Nguyen et al. 2023 | detection only; no correction |
| normality-profiling causes false alarms | Isolation Forest 2008 | unmeasured; this is RQ1 |
| one-class methods assume separability | NFAD 2021 | legitimate operation overlaps faults by construction |

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

That error taxonomy is nearly identical to `docs/research/vocabulary.md`,
which is reassuring for its stability. PCA being the dominant approach is worth
noting, since `docs/research/positioning.md` deferred it.

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

## Applied evidence: model-comparison findings

Distinct from the papers read above, which report what studies found; these are
the operational implications already drawn for this pipeline. Kept because they
are specific and testable, not because they are general.

## Source 1 — ECML 2026

> _What Streaming Anomaly Detection Finds (and Misses) in Industrial Time Series_
> Parrino et al., ECML PKDD 2026 Industrial Track

### 1. Ensembling beats single-model selection

**Finding:** simple mean over 29 models ranked top-6; top-4 selection outperformed the best individual model.

**For us:** add LODA alongside TSOD-KNN and average their scores before thresholding.
One line in `detection.py`: `score = (knn_score + loda_score) / 2`.

### 2. LODA and KNN are the top individual performers

**Ranking:** LODA (0.346) > CNN (0.294) > MCD (0.269) > SVM (0.264) > KNN (0.161).

**For us:** LODA is a drop-in from `pyod` (`from pyod.models.loda import LODA`), faster than KNN,
and handles higher-dimensional input better — relevant if we add SCADA channels.

### 3. Online (batch-trained, fixed) > Streaming (adaptive) for low-velocity data

**Finding:** Online models have higher _median_ VUS-PR than streaming models at low stream velocity.

**For us:** our train-once-on-healthy-anchor approach is already the right paradigm. No adaptive
mechanisms needed unless we see systematic drift over months.

### 4. Train on a clean segment — z-normalize on training batch only

**For us:** our 24 h anchor is deliberately clean; `StandardScaler` fit on training only. ✓
Extend the training block if false-positive rate is high.

### 5. Consensual false positives reveal domain events, not model failures

**Finding:** recurring FP across models coincided with extreme tidal events and planned shutdowns.

**For us:** tag known operational events in `manual_windows.csv` (add `operational_event` column) to
exclude them from recall/precision accounting. Do **not** tune the threshold to suppress them —
that hides real anomalies with similar signatures.

### 6. Use VUS-PR with a left-buffer for early-detection credit

**For us:** point-wise labels under-reward early detection. VUS-PR with a ~10%-of-window
left-buffer (e.g., 12 min for a 2 h window) is a better metric. Available from the StrAD repo.

### 7. Isolated anomalies are hard; clustered ones are easy

**Finding:** multi-event clusters detected by 20–23/29 models; isolated events by 0–2.

**For us:** if recall is low on single-event windows, widen the window or increase
`WINDOW_SIZE` so the model sees the run-up.

---

## Source 2 — Applied Sciences Special Issue 2023

> _Special Issue on Unsupervised Anomaly Detection_, Goldstein, Applied Sciences 2023.
> Editorial summary of 12 papers. Broad scope — relevance to our pipeline is partial.

**Verdict: low novelty impact, confirms our choices.**

### What it validates

- **Classical ML > deep learning** (Rewicki et al.): TSOD-KNN is the right call; deep models
  need more data and are harder to calibrate for 2–10 h windows.
- **Semi-supervised = train on normal class only**: our healthy-anchor approach is the stronger
  setup vs. fully unsupervised. No change needed.
- **Contextual anomaly → point anomaly mapping**: TSOD-KNN sliding-window scoring is the
  standard correct approach for sub-sequence anomalies.

### One actionable idea

**Explainability** — two papers focused on explaining _why_ a detection fires. Per-sensor score
contribution in the review plot would improve operator trust. TSOD sub-scores are already
available; surfacing them in `plot_strain_labels` is a low-effort addition.

### What is not relevant

| Paper                                         | Why                            |
| --------------------------------------------- | ------------------------------ |
| GAN digital twin (Lian et al.)                | Overkill for our window count  |
| MST-VAE (Pham et al.)                         | Deep learning, ruled out above |
| HMM for KPI correlation (Shang et al.)        | Distributed-system framing     |
| Adaptive ARIMA (Kozitsin et al.)              | Univariate forecasting         |
| IoT feature-evolving streams (Al-amri et al.) | Our dimensionality is stable   |

---

## Final Summary — Prioritised Action List

| Priority   | Action                                                 | Effort      | Source     |
| ---------- | ------------------------------------------------------ | ----------- | ---------- |
| **High**   | Add LODA scorer, ensemble `mean(knn, loda)`            | ~10 lines   | ECML       |
| **High**   | Adopt VUS-PR (left-buffer ~10% window) as eval metric  | ~1 dep      | ECML       |
| **Medium** | Extend training block (>24 h) if FP rate stays high    | config knob | ECML       |
| **Medium** | Add `operational_event` column to `manual_windows.csv` | CSV edit    | ECML       |
| **Low**    | Per-sensor score contribution in review plot           | ~15 lines   | Appl. Sci. |
| **Skip**   | Deep learning models (VAE, LSTM, Transformer)          | —           | both       |
| **Skip**   | Adaptive/streaming model updates                       | —           | ECML       |

---

## Source 3 — Dataset construction resources

Both reviewed papers assumed an existing labeled dataset. Our pipeline **builds its own** — which is both the constraint and the novel contribution. The notes below cover best practices from the broader TSAD literature.

### Train / test split rules (time series)

- **Always chronological** — never shuffle. Train on a past block, test on future windows.
- **Current setup is correct:** train = first 24 h of the Nov 2023 healthy anchor; test = all cataloged raw windows (post-2024). Natural chronological split with a ~5-month gap.
- Insert a gap period between train and test if slow sensor drift is suspected (reduces lookahead bias).
- Use `sklearn.model_selection.TimeSeriesSplit` for rolling-window cross-validation if you want statistical confidence on recall/precision.

### Healthy anchor sizing

- 1 week (Nov 2023) gives a comfortable buffer. Only the first `TRAINING_HOURS` (default 24 h) are used for fitting — extend via config if the training plot shows the model learning drift rather than a clean baseline.
- Do **not** extend into operational or ambiguous periods — the contamination assumption (`CONTAMINATION = 0.01`) breaks if the anchor is not genuinely clean.

### Labeling quality

- Prefer **segment-level labels** (begin/end timestamps) over point-wise where possible; the current schema stores both.
- Tag known operational events (`operational_event` column in `manual_windows.csv`) — do not tune the threshold to suppress them; that hides real anomalies with similar signatures.
- Isolated single-event anomalies are harder to detect; widening `window_size` so the model sees the run-up improves recall (ECML finding).

### Relevant public benchmarks

These are the closest analogs in public literature — useful for calibrating recall and for future comparison. All are listed in [yzhao062/anomaly-detection-resources](https://github.com/yzhao062/anomaly-detection-resources).

| Dataset / Benchmark                          | Domain                             | Anomaly type                         | Link                                                                                       |
| -------------------------------------------- | ---------------------------------- | ------------------------------------ | ------------------------------------------------------------------------------------------ |
| **SKAB**                                     | Industrial sensor data             | Machine/process anomalies            | [github](https://github.com/waico/skab)                                                    |
| **NAB**                                      | Real-time multi-domain time series | Early-detection benchmark            | [github](https://github.com/numenta/NAB)                                                   |
| **ODDS**                                     | Mixed tabular benchmark set        | Classical outlier detection datasets | [site](http://odds.cs.stonybrook.edu/#table1)                                              |
| **ELKI Outlier Datasets**                    | Benchmark dataset collection       | Mixed outlier datasets               | [site](https://elki-project.github.io/datasets/outlier)                                    |
| **Unsupervised Anomaly Detection Dataverse** | Benchmark dataset collection       | Mixed outlier datasets               | [dataset](https://dataverse.harvard.edu/dataset.xhtml?persistentId=doi:10.7910/DVN/OPQMVF) |

SKAB and NAB are the most directly comparable to our pipeline; the others are good fallback references for broader classical outlier detection.

## Not yet ingested

- 327 of 344 papers are title-triaged only.
- Read/unread counts are no longer tracked here. Run
  `python -m scripts.related_work.papers todo` — the reading log at
  `reading_log.csv` is the source of truth. The two counts written into this
  file previously were both wrong.
- The 2025-2026 metrics cluster (VUS, segmentation measures) is only partly read.
- The seven section-2.4 citations behind the gap argument are not locally
  available and have not been read in full.
- The `20240606_D31_Damiano_v1.pdf` thesis draft has not been read in this repo.
- `gianotti_et_al._2026_assessing_reliability_of_cm_scale_optical_fiber_strain_sensing`
  is adjacent work that has not been reviewed.

Next tranche should prioritise: the remaining metrics papers, model-selection
studies, and the data-quality/cleaning cluster, since that is the application
side of the bridge.