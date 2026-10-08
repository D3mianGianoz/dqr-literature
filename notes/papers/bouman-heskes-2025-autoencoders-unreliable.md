# Bouman & Heskes (2025) — *Autoencoders for Anomaly Detection Are Unreliable*

The paper studies the assumption that normal data should have lower
autoencoder reconstruction loss than anomalous data. It proves that PCA and
linear autoencoders can reconstruct some points arbitrarily far from the
training data with zero loss. For nonlinear networks, it gives a simple ReLU
construction and experiments on synthetic tabular data and MNIST showing
out-of-bounds reconstruction and interpolation between classes. These cases
can assign low reconstruction loss to anomalous inputs.

The effect is not universal: the MNIST examples vary with initialization and
the choice of normal classes, and some low-loss out-of-bounds regions are
consistent with plausible normal variation. The authors conclude that
reconstruction loss alone is not a reliable anomaly score, especially when
reconstruction outside the training-data bounds is unconstrained. Their
experiments concern tabular and image data; they do not establish how often
these failure modes occur in industrial strain time series. They recommend
checking trained autoencoders for undesirable out-of-bounds reconstruction.
