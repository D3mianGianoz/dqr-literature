# Bouman (2025) — *Rethinking Anomaly Detection: From Theory to Practice*

This dissertation brings together the 2024 33-algorithm/52-dataset benchmark, an analysis of why reconstruction-error autoencoders can fail, and an applied power-grid time-series study. Its central operational recommendation is a small, interpretable toolkit: kNN for local anomalies and Extended Isolation Forest (EIF) for global anomalies in the tabular benchmark; it explicitly leaves their transfer to raw time series for tailored evaluation.

The grid application is the closer analogue for crane data. It separates short anomalies from sustained baseline changes: statistical process control and Isolation Forest detect short events, while binary segmentation detects long switch events. A sequential ensemble—segment first, then apply SPC or IF only within segments judged normal—outperformed simple OR-combination ensembles because the latter gained recall at the cost of too many false positives. The best sequential setup produced load estimates within 10% of the reference in about 90% of 60 held-out station measurements.

The grid result used supervised tuning on labelled data and a station-specific bottom-up reference signal, so it motivates a hypothesis rather than validating transfer to crane strain.
