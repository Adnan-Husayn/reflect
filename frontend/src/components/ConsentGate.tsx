interface ConsentGateProps {
  onAccept: () => void;
}

/**
 * Shown once, before the first check-in is ever submitted.
 *
 * Item-level responses are stored, not just the total — that is what allows
 * rescoring and it is what a methods section has to describe — so the consent
 * copy says so plainly rather than mentioning only the score.
 */
export function ConsentGate({ onAccept }: ConsentGateProps) {
  return (
    <section className="consent-gate" aria-labelledby="consent-heading">
      <h2 id="consent-heading">Before your first check-in</h2>

      <dl>
        <div>
          <dt>What is collected</dt>
          <dd>
            Your answer to each of the eight questions, and the total they add up to. Answers are
            stored individually, not only as a score.
          </dd>
        </div>
        <div>
          <dt>Why</dt>
          <dd>
            To measure whether this project&rsquo;s multimodal index tracks a validated
            questionnaire. That comparison is the point of the study.
          </dd>
        </div>
        <div>
          <dt>Taking part is optional</dt>
          <dd>
            You can use every other part of Reflect without ever filling this in, and you can stop
            at any time without giving a reason.
          </dd>
        </div>
        <div>
          <dt>Withdrawing</dt>
          <dd>
            Deleting your data removes every check-in and every recorded session outright. It is not
            marked hidden or archived — the rows are gone, and it cannot be undone.
          </dd>
        </div>
        <div>
          <dt>What this is not</dt>
          <dd>
            Not a diagnosis and not a clinical assessment. No result here is interpreted or graded,
            and no one is monitoring your answers.
          </dd>
        </div>
      </dl>

      <button type="button" className="secondary-button" onClick={onAccept}>
        I understand — continue
      </button>
    </section>
  );
}
