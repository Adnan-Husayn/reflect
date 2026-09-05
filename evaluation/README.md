# Evaluation notes

Evaluate each modality independently first: per-channel accuracy is what the fusion weights are derived from, so a combined score computed before those numbers exist would be circular.

The fused output is then evaluated as its own system, against the same labelled data:

- **Fusion weights** come from measured per-modality reliability (inverse-error or accuracy-proportional), not from taste. Equal weights are the current placeholder.
- **The conflict threshold** (`conflict_threshold`, provisionally 0.35) should be derived from the divergence distribution on labelled data, reported with an ROC curve rather than picked by hand.
- **Attenuation** should be checked for the property it exists to guarantee: that readings whose channels disagree are not reported as confident.

RAVDESS is well suited to the threshold work: its actors speak fixed, emotionally neutral sentences with different emotional deliveries, so the text channel is neutral by construction while voice and face carry the emotion. That gives labelled cross-modal disagreement without staging it yourself.

When a labelled dataset is available, add modality-specific samples under this directory:

```text
evaluation/
  text-samples/
  audio-samples/
  facial-samples/
```

For each modality, record the expected canonical label (`anger`, `disgust`, `fear`, `joy`, `neutral`, `sadness`, or `surprise`) and compare it with the API response. Useful later measures include per-class precision, recall, F1 score, and a confusion matrix. Keep the samples and consent process appropriate for sensitive voice and facial data.

For the live session, evaluate short English audio segments separately for transcription quality, vocal prediction, and transcript-text prediction. Compare the replacement facial-expression checkpoint with the previous checkpoint on the same consented, labelled image set before making accuracy claims. Facial output must be reported as a visible-expression indicator, not ground truth about a participant's internal emotional state.
