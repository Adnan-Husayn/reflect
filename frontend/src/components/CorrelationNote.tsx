import type { Correlation } from "../types/emotion";

/**
 * States the correlation and, more importantly, its weakness.
 *
 * Below the minimum pair count nothing is rendered but the reason — the same
 * gap-not-zero rule the daily buckets use. Where a value is shown, n is shown
 * beside it, because with weekly check-ins over one term n lands around 8-10:
 * a real result, and nowhere near significance.
 */
export function CorrelationNote({ correlation }: { correlation: Correlation }) {
  const { r, n, minimum_pairs } = correlation;

  return (
    <section className="correlation-note" aria-labelledby="correlation-heading">
      <h3 id="correlation-heading">Does the index track the questionnaire?</h3>

      {r === null ? (
        <p className="correlation-pending">
          Not enough paired observations yet — {n} of the {minimum_pairs} needed. A pair is a day
          with both a recorded session and a check-in. Nothing is reported until there are enough,
          because a coefficient from a handful of points invites more confidence than it can carry.
        </p>
      ) : (
        <>
          <p className="correlation-value">
            <strong>r = {r.toFixed(2)}</strong>
            <span>over n = {n} paired days</span>
          </p>
          <p className="correlation-caption">
            Pearson correlation between each day&rsquo;s mean valence and that day&rsquo;s PHQ-8
            score. A <strong>negative</strong> value is the direction that would support the
            hypothesis, since PHQ-8 rises as wellbeing falls while valence does the opposite.
          </p>
        </>
      )}

      <p className="correlation-caveat">
        This is a within-subject correlation over a small sample. It is not evidence of a general
        relationship between the two measures, it is not a significance test, and it says nothing
        about anyone other than this user.
      </p>
    </section>
  );
}
