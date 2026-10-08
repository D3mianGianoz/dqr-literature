# Parrino et al. (2026) — *What Streaming Anomaly Detection Finds (and Misses) in Industrial Time Series*

ECML PKDD 2026 Industrial Track.

The study reports that a simple mean over 29 models ranked in the top six and
that selecting the top four models outperformed the best individual model.
LODA ranked ahead of CNN, MCD, SVM, and KNN among the listed individual
performers. At low stream velocity, online models had higher median VUS-PR
than streaming adaptive models.

The authors report that recurring false positives across models coincided with
extreme tidal events and planned shutdowns. Their VUS-PR evaluation uses a
left buffer to credit early detections. Clustered anomalies were detected by
20–23 of the 29 models, while isolated anomalies were detected by 0–2.

These results describe the paper's industrial time-series setting. They do not
establish that the same ranking, operating regime, or buffer choice transfers
to another dataset.
