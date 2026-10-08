# Literature synthesis: sensor-data quality and anomaly detection

This review synthesizes recurring findings across the literature. Source-level
claims, qualifications, and open checks live in [`notes/papers/`](notes/papers/README.md).
The AUO study's questions, design, and decisions live in its
[project-facing reference register](../jupiler-22013_auo/docs/research/references.md).

## Synthesis

Anomaly detection is one component of sensor-data verification, not a complete
data-cleaning or fault-diagnosis system. Data-quality work also covers defining
requirements, assessing data against them, and acting on the assessment. A
statistical flag alone does not establish that a sensor is faulty or justify
correcting or discarding a reading. Sensor faults are domain-relative, while
unusual measurements can reflect either measurement problems or legitimate
system behaviour. These distinctions recur in the work on [data-quality
frameworks](notes/papers/cichy-rass-2019-an-overview-of-data-quality-frameworks.md),
[sensor fault taxonomies](notes/papers/ni-et-al-2009-sensor-network-data-fault-types-acm-tosn-5-3.md),
and [anomaly definitions](notes/papers/topic-summaries.md).

Evaluation must match the task and the unit being evaluated. Point metrics do
not fully represent range or episode detections, and class imbalance changes
how ROC and precision-recall results should be interpreted. Benchmarking work
favours scenario-specific comparisons and analysis by pipeline component.
Results on tabular data do not establish transfer to strain time series; models
trained on assumed-normal data also carry a contamination risk. See the notes on
[range-based evaluation](notes/papers/tatbul-lee-alam-bekiroglu-2018-precision-and-recall-for-time-series.md),
[ROC and precision-recall](notes/papers/davis-goadrich-2006-the-relationship-between-precision-recall-and-roc-curves.md),
[benchmarking](notes/papers/rochner-et-al-2025-we-need-to-rethink-benchmarking-in-anomaly-detection-position-paper.md),
and [contaminated training data](notes/papers/donne-davis-2026-robust-anomaly-detection-under-contaminated-data.md).

Sensor and structural-health-monitoring literature adds context that general
benchmarks omit. Observable fault descriptions can be useful without asserting
physical cause. Sensor state, physical range, operational context, and
relationships across sensors can inform interpretation, provided their
independence from labels and model design is clear. Natural faults can support
benchmark datasets when labels and their limits are explicit; fault injection
also remains a recognized testing practice. These points are discussed in the
notes on [sensor-data benchmarks](notes/papers/de-bruijn-meratnia-et-al-2016-benchmark-datasets-for-fault-detection-and-classification-in.md),
[fault taxonomies](notes/papers/ni-et-al-2009-sensor-network-data-fault-types-acm-tosn-5-3.md),
and [additional sensor literature](notes/papers/topic-summaries.md).

These findings motivate task-specific evaluation and careful interpretation;
they do not establish that a particular detector works on crane strain data.
Project choices and status belong in the AUO study repository. Corpus and
reading progress come from `data/inventory.csv` and `data/reading_log.csv`; use
`uv run python -m related_work.papers todo` for current progress.
