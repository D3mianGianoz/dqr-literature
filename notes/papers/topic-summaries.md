# Topic summaries of additional literature

These selective notes group references that were summarized thematically in
the former review. They are not a reading-status record; consult
`data/reading_log.csv` or run `uv run python -m related_work.papers todo`.

## Data quality and sensor validation

Data quality is multidimensional and depends on use, as discussed by Wang &
Strong (1996), Strong et al. (1997), and Cichy & Rass (2019). Sensor-stream
work applies this framing to operational data (Klein & Lehner, 2009). Scholl et
al. (2023) explore combining quality attributes into an interpretable value.

Mourad & Bertrand-Krajewski (2002) describe automatic pre-validation of long
time series using tests for sensor state, physical range, locally realistic
range, and elapsed time. Jeffery et al. (2006) present ESP, a declarative
pipeline framework for sensor-data cleaning. These works concern validation
and cleaning systems as well as anomaly scoring.

## Anomaly definitions and fault descriptions

Chandola et al. (2009) describe the difficulty of defining a boundary between
normal and anomalous behaviour. Hodge & Austin (2004) distinguish changes in
system behaviour from mechanical faults and instrument errors as possible
causes of outliers. Baljak et al. (2012) classify faults by continuity,
frequency, and observable or learnable patterns independently of underlying
cause. Ni et al. (2009) provide a sensor-data fault taxonomy and discuss both
calibration faults and injected faults in system testing.

## Detection methods and benchmarks

Isolation Forest (Liu et al., 2008) discusses the false-alarm trade-off of
methods that profile normal instances. Extended Isolation Forest (Hariri et
al., 2021) addresses score artifacts. LOF (Angiulli & Pizzuti, 2002), HBOS
(Goldstein & Dengel, 2012), and one-class approaches provide method-specific
primaries; Ryzhikov et al. (2021) discuss the separability assumption in
one-class detection. Ensemble Grammar Induction (Gao et al., 2020) identifies
unsupervised discretization choices as an open issue.

Surveys by Chandola et al. (2009), Pang et al. (2022), Schmidl et al. (2022),
and Erhan et al. (2021) cover anomaly detection across general, time-series,
and sensor-system settings. Applied sensor work includes Kaiser et al. (2005),
Javed & Wolf (2012), Ayadi et al. (2017), Ahmad et al. (2017), and Holbert &
Lin (2012). Their domains differ, so they provide context rather than direct
validation for any particular sensor application.

## Metrics and temporal methods

Bradley (1997) surveys AUC as a classifier performance measure; Davis &
Goadrich (2006) analyze the relationship between ROC and precision-recall
curves under class skew. Breunig et al. (2000) model outlierness as a degree,
while Keogh et al. (2002) discuss limitations in definitions of temporal
surprise. Rasheed et al. (2009) apply FFT methods to spatial outlier mining.

## Foundational and adjacent references

Zimek & Filzmoser (2018) review the relationship between statistical and
data-mining approaches to outlier detection. Aggarwal (2017), Kingma & Welling
(2014), Hochreiter & Schmidhuber (1997), and Sutton & Barto (2018) are
foundational references for data models, generative methods, recurrent
networks, and reinforcement learning respectively; they are adjacent context,
not evidence of performance on strain time series.
