# Ni, et al. (2009) — Sensor network data fault types (ACM TOSN 5(3))

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
measurements but not necessarily lower **precision**." The paper also states
that detecting and modelling general calibration errors is "difficult without
human input."

For system testing, Ni et al. recommend injecting common faults into simulated
or real datasets. This is a testing recommendation, separate from their
taxonomy and calibration-fault descriptions.
