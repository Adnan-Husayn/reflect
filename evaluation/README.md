# Evaluation harness — RAVDESS

**Milestone M2. Owner: Hashir.**

This harness exists to replace four guesses in `backend/app/config.py` with four
measured values:

```python
conflict_threshold: float = 0.35  # provisional
fusion_weight_text: float = 1.0  # provisional
fusion_weight_voice: float = 1.0  # provisional
fusion_weight_face: float = 1.0  # provisional
```

Until those come from data, every accuracy claim the project makes rests on
numbers somebody picked by hand. That is the single biggest hole in the report,
and closing it is what M2 is for.

## Why RAVDESS

The Ryerson Audio-Visual Database of Emotional Speech and Song: 24 professional
actors, 12 male and 12 female, performing eight emotions. Free from Zenodo,
CC BY-NC-SA 4.0, cite it in the report.

Three properties make it the right corpus here.

**It is audiovisual.** One clip carries both the voice and the face, labelled
with the same emotion at the same instant. Fusion combines channels *for one
moment*, so it cannot be evaluated on three unrelated single-modality datasets.

**Both sentences are emotionally inert.** Every actor says only *"Kids are
talking by the door"* or *"Dogs are sitting by the door"*. The words carry no
emotion regardless of how they are performed, so the transcript-text channel has
a known ground truth of `neutral` on every clip in the corpus.

**That gives conflict labels for free.** On an angry clip, text truth is neutral
while voice and face truth is anger — a labelled cross-channel disagreement. On
a neutral clip, all three agree. Positive and negative examples of conflict, with
no annotation work, which is exactly what deriving a threshold requires.

## The one mistake that would invalidate everything

**Split by actor, never by clip.**

Each of the 24 actors performs the same two sentences in all eight emotions. Put
the same actor in both training and held-out data and the models partly learn
*"this is actor 14"* rather than *"this is anger"*. Every number then comes out
inflated, and the inflation is invisible in the output.

`manifest.py` splits by actor and `assert_actor_disjoint` fails the build if the
partition ever leaks. Do not work around it. Expect to be asked about this in
the viva; the answer is that actors 19–24 were never seen during fitting.

## Setup

```bash
cd evaluation
python -m venv .venv && source .venv/bin/activate
pip install -r requirements-dev.txt
```

`ffmpeg` must be on `PATH` for the extraction step:

```bash
brew install ffmpeg
```

## Step 1 — download

Get the **full audio-video speech** set from the Zenodo record
(`Video_Speech_Actor_01.zip` … `_24.zip`, roughly 15 GB in total). Confirm the
exact filenames on the record page rather than guessing the URLs.

Song files are excluded on purpose: they cover only six of the eight emotions
and actor 18 has none of them, so including them would quietly unbalance the
classes. `discover_clips` filters them out already.

Extract everything under `evaluation/data/raw/`. The directory layout does not
matter — every file carries its own labels in its filename, and the harness
walks the tree recursively.

## Step 2 — build the manifest

```bash
python scripts/build_manifest.py --root data/raw --out data/manifest.csv
```

Reads filenames only, so it finishes in seconds. Run it before extraction — it
is the cheapest way to catch a partial download.

Check the printed summary before going further:

- **1,440 clips** for the full audio-video speech set (1,080 train / 360 held-out)
- **18 train actors / 6 held-out**, and no actor in both
- 8 clips per emotion per actor, except `neutral` at 12. Neutral is the *largest*
  class under the default merge, because it absorbs `calm`: RAVDESS records no
  "strong" intensity for neutral itself (4 clips) but does for calm (8). Under
  `--calm drop`, neutral instead becomes the smallest class at 4
- a conflict balance of **4:1** — 288 conflict against 72 aligned in the held-out
  split. Worth remembering when reading the ROC: a classifier that always
  answered "conflict" would score 80% accuracy while being useless, which is why
  the threshold is chosen off the curve and not off accuracy

`--calm drop` excludes the calm class instead of merging it into `neutral`.
Merging is the default and the usual choice in the literature, but it *is* a
choice: state which one you used and why.

## Step 3 — extract audio and frames

```bash
python scripts/extract_media.py --manifest data/manifest.csv --out data/prepared
```

Each `.mp4` becomes one 16 kHz mono WAV plus five JPEG frames. Slow and IO-bound;
idempotent, so an interrupted run can just be restarted.

Frames come from the middle 20–80% of each clip, not the whole of it. RAVDESS
recordings open and close on a near-neutral face, so frames from the very start
would be labelled with an emotion that is not on the actor's face yet. Five
frames also mirrors the live session's own five-frame smoothing, which keeps the
measurement close to what the running app does.

## Step 4 — score through the API

Start the backend first:

```bash
cd ../backend && uvicorn app.main:app
```

Then smoke-test on a handful of clips before committing to a full run:

```bash
python scripts/score.py --limit 10 --out data/smoke.jsonl
```

Check a record by eye: are the score vectors sensible, does `fusion` come back
populated, how many frames returned no face? Then run the real thing:

```bash
python scripts/score.py --split held_out --out data/scores.jsonl
```

Writes JSONL and appends as it goes, so it resumes cleanly after an interrupt.

Run it **twice**, once per text source, and report both:

- `--text-source statement` (default) scores the known sentence, isolating the
  emotion models from transcription error
- `--text-source transcript` scores what Whisper actually heard, which is what
  the live session really does

The gap between the two is your transcription cost, and it belongs in the
report. RAVDESS actors are North American; your users are Indian English
speakers, so expect this gap to be larger in the field than it is here — and say
so in the limitations section.

## Step 5 — the analysis

```bash
python scripts/report.py --scores data/scores.jsonl --out results/
```

`scripts/report.py` is **deliberately unfinished**. The plumbing either side of
it is written; the analysis is the actual milestone work. Each of its four
functions states exactly what it must return and what the result feeds:

| Function | Produces | Feeds |
| --- | --- | --- |
| `per_modality_metrics` | accuracy, macro F1, three confusion matrices | the report |
| `fusion_weights` | three weights summing to 1 | `fusion_weight_*` in config |
| `conflict_threshold` | ROC, AUC, chosen operating point | `conflict_threshold` in config |
| `fusion_comparison` | fused vs each single channel | the report's central claim |

Everything reads the **held-out split only**.

Three things to keep honest while writing them:

**The text channel's ground truth is `neutral` on every clip.** Its accuracy is
therefore not comparable with the other two, and must not be read as "the text
model is worse". Say this explicitly in the report.

**Report the AUC even if it disappoints.** An AUC near 0.5 would mean divergence
does not separate conflict from agreement at all. That is a real finding about
the method, and it is worth more than a threshold quietly tuned until it looked
good.

**A negative fusion result is still a result.** If fusion does not beat the best
single channel, report that. A measured negative beats an unmeasured positive,
and examiners can tell the difference.

## Step 6 — fine-tuning

Fine-tune at least one modality's classification head on the **train** actors,
then re-run steps 4 and 5 unchanged and report before/after on the same held-out
split. This is also what makes §3.1's "custom-trained" wording honest while
staying inside §4.1.2's exclusion of training from scratch.

## Step 7 — write the values into config

```python
conflict_threshold:  float = <from results/threshold.json>
fusion_weight_text:  float = <from results/config_values.json>
fusion_weight_voice: float = <from results/config_values.json>
fusion_weight_face:  float = <from results/config_values.json>
```

Update the comments above them at the same time — they currently say
"provisional" and point at this harness. Once the numbers are derived, they
should point at the results instead.

## Limitations to state in the report

Write these down now, while they are obvious, rather than reconstructing them in
December.

**Acted, not spontaneous.** Actors performing anger differ measurably from
people who are angry. Models evaluated on acted corpora overstate real-world
performance, and this is well documented.

**Accent mismatch.** 24 North American English speakers; your users speak Indian
English. This affects both Whisper's transcription and the prosody model, and
nothing in these results measures that gap.

**Conflict here is a proxy.** A neutral sentence delivered angrily is not the
same phenomenon as a person masking distress. It is a defensible way to
operationalise cross-channel disagreement, but describe it as one.

**Non-commercial licence.** CC BY-NC-SA 4.0. Fine for academic work; cite it.

## If there is time

CREMA-D — 91 actors, considerably more ethnically diverse, also audiovisual —
would strengthen any generalisation claim. Treat it as a stretch goal. One
dataset done properly beats two done carelessly.

## Testing

```bash
pytest
ruff check .
```

The tests cover filename parsing and the actor-disjoint split, which are the two
places where a silent error would corrupt every number downstream. They need no
data files and run in under a second.
