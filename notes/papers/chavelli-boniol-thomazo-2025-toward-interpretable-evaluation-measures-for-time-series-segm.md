# Chavelli, Boniol & Thomazo (2025) — *Toward Interpretable Evaluation Measures for Time Series Segmentation* (arXiv:2510.23261)

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
