# Evaluation notes

v0.1 evaluates text, audio, and facial-expression predictions independently. No combined score should be calculated during evaluation.

When a labelled dataset is available, add modality-specific samples under this directory:

```text
evaluation/
  text-samples/
  audio-samples/
  facial-samples/
```

For each modality, record the expected canonical label (`anger`, `disgust`, `fear`, `joy`, `neutral`, `sadness`, or `surprise`) and compare it with the API response. Useful later measures include per-class precision, recall, F1 score, and a confusion matrix. Keep the samples and consent process appropriate for sensitive voice and facial data.

For the live session, evaluate short English audio segments separately for transcription quality, vocal prediction, and transcript-text prediction. Compare the replacement facial-expression checkpoint with the previous checkpoint on the same consented, labelled image set before making accuracy claims. Facial output must be reported as a visible-expression indicator, not ground truth about a participant's internal emotional state.
