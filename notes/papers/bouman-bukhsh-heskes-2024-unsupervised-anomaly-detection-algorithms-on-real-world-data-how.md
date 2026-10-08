# Bouman, Bukhsh & Heskes (2024) — *Unsupervised Anomaly Detection Algorithms on Real-world Data: How Many Do We Need?* (JMLR 25)

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
