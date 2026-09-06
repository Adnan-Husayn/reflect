import { Link } from "react-router-dom";
import { DivergenceField } from "../components/DivergenceField";
import type { AuthState } from "../hooks/useAuth";

const CHECKPOINTS = [
  ["Text", "j-hartmann/emotion-english-distilroberta-base"],
  ["Audio", "superb/wav2vec2-base-superb-er"],
  ["Transcription", "faster-whisper base.en"],
  ["Facial", "dima806/facial_emotions_image_detection"],
];

/**
 * Absences, stated plainly. In this domain that reads as credibility.
 *
 * Rewritten against the shipped app rather than the design canvas: the canvas
 * was drawn at v0.3 and still claims "no combined score" and "no accounts, no
 * history", both of which fusion and persistence made false.
 */
const ABSENCES = [
  [
    "No diagnosis or risk score",
    "It is an emotion indicator. It makes no clinical assessment and gives no treatment recommendation.",
  ],
  [
    "No score without its components",
    "The channels are fused into one reading, but the three are always shown beside it. Disagreement between them lowers the combined confidence rather than being hidden by it.",
  ],
  [
    "No severity bands",
    "The check-in questionnaire is scored and plotted. No total is ever mapped onto a category or a cutpoint.",
  ],
  [
    "No recordings kept",
    "Audio, camera frames and transcripts are processed in memory and never written to the database. Only derived score vectors are stored, and deleting your data removes them outright.",
  ],
  [
    "No analytics or telemetry",
    "Nothing about a session is measured, counted or sent anywhere. Your account is visible to nobody else.",
  ],
  [
    "No generated replies",
    "Reflect does not respond, counsel or converse. Every suggestion it shows was written by hand in advance.",
  ],
];

interface LandingProps {
  account: AuthState;
}

export function Landing({ account }: LandingProps) {
  const signedIn = account !== null && account !== "loading";

  return (
    <main className="landing">
      <section className="landing-hero">
        <div className="page-shell">
          <p className="project-code">Multimodal emotion and mental health analytics</p>
          <h1 className="landing-headline">
            Three readings.
            <br />
            Never one score alone.
          </h1>
          <p className="landing-lead">
            Reflect transcribes short spoken-English segments on your own machine and reads what you
            said, how you said it, and how you looked. It combines them into one reading — and never
            shows that reading without the three it came from. It does not diagnose.
          </p>
          <div className="landing-actions">
            {signedIn ? (
              <Link to="/session" className="landing-cta">
                Go to your session
              </Link>
            ) : (
              <>
                <Link to="/register" className="landing-cta">
                  Create an account
                </Link>
                <Link to="/login" className="landing-secondary">
                  Sign in
                </Link>
              </>
            )}
          </div>
        </div>

        <DivergenceField />
      </section>

      <section className="landing-section">
        <div className="page-shell">
          <p className="landing-eyebrow">How a session is read</p>
          <h2 className="landing-h2">Three models, running side by side.</h2>
          <div className="landing-columns">
            <div>
              <h3 style={{ color: "var(--channel-text)" }}>Spoken words</h3>
              <p>
                Five-second microphone segments are transcribed on your own machine by
                faster-whisper, then classified by a seven-class English DistilRoBERTa model. The
                audio never leaves the device.
              </p>
            </div>
            <div>
              <h3 style={{ color: "var(--channel-voice)" }}>Vocal expression</h3>
              <p>
                The same segment is resampled to 16&nbsp;kHz and scored by a Wav2Vec2
                speech-emotion checkpoint. This channel reads tone, not content — it does not know
                what you said.
              </p>
            </div>
            <div>
              <h3 style={{ color: "var(--channel-face)" }}>Visible facial expression</h3>
              <p>
                A camera frame every two seconds. The largest face is selected and the reading is
                averaged across the last five frames, so a single blink cannot move it.
              </p>
            </div>
          </div>
          <p className="landing-note">
            If the microphone is denied, the camera keeps running. If no face is visible, the other
            two channels carry on. Each channel fails on its own.
          </p>
        </div>
      </section>

      <section className="landing-section">
        <div className="page-shell landing-narrow">
          <p className="landing-eyebrow">When the channels disagree</p>
          <h2 className="landing-h2">Disagreement is the interesting signal.</h2>
          <p className="landing-body">
            Reflect compares the latest score vector from each channel using Jensen–Shannon
            divergence on a base-2 logarithm, so the figure is bounded between zero and one: nought
            means the channels agree exactly, one means they share no probability mass at all.
          </p>
          <p className="landing-body">
            That same number attenuates the combined confidence. A reading built from channels that
            contradict each other is reported as low confidence rather than as a confident label —
            which is what stops a weighted average from sounding certain when it should not.
          </p>
          <p className="landing-caveat">
            A conflict means the channels disagree. It is <strong>not</strong> evidence that a
            person is concealing an emotion, and it is not a diagnosis.
          </p>
          <p className="landing-body landing-dim">
            The 0.35 threshold is provisional. It separates strong conflicts from ordinary variation
            but misses subtler disagreement, and it has not yet been derived from held-out labelled
            data. Deriving it is the next milestone, and no accuracy claim should be published
            before then.
          </p>
        </div>
      </section>

      <section className="landing-section">
        <div className="page-shell">
          <p className="landing-eyebrow">What Reflect does not do</p>
          <h2 className="landing-h2">The absences are deliberate.</h2>
          <dl className="landing-absences">
            {ABSENCES.map(([title, detail]) => (
              <div key={title}>
                <dt>{title}</dt>
                <dd>{detail}</dd>
              </div>
            ))}
          </dl>
        </div>
      </section>

      <section className="landing-section">
        <div className="page-shell">
          <p className="landing-eyebrow">Provenance</p>
          <h2 className="landing-h2">The models are not ours.</h2>
          <p className="landing-body landing-narrow-p">
            The team built the architecture, the processing pipeline, the API, the interface and the
            integration. The four checkpoints below are externally published pretrained models, each
            with its own authors, licence and intended-use notes.
          </p>
          <div className="landing-table">
            {CHECKPOINTS.map(([modality, checkpoint]) => (
              <div key={modality}>
                <span>{modality}</span>
                <span className="mono">{checkpoint}</span>
              </div>
            ))}
          </div>
          <div className="landing-figures">
            <div>
              <strong className="mono">7</strong>
              <span>canonical labels, normalised across every model</span>
            </div>
            <div>
              <strong className="mono">319</strong>
              <span>tests, run in CI on every push and pull request</span>
            </div>
            <div>
              <strong className="mono">9</strong>
              <span>constants still provisional, pending the evaluation</span>
            </div>
          </div>
        </div>
      </section>

      <footer className="landing-footer">
        <div className="page-shell">
          <p>
            Visible facial expression and model confidence are indicators only. Reflect is not a
            diagnosis, a substitute for therapy, or a measure of a person&rsquo;s internal emotional
            state, and it should not be used to make medical, employment, safety or other
            high-impact decisions.
          </p>
          <p className="mono landing-colophon">PCS26/146 · Integral University Lucknow</p>
        </div>
      </footer>
    </main>
  );
}
