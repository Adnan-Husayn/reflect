import type { Wellbeing } from "../types/emotion";

/**
 * The headline is never shown alone.
 *
 * The whole `Wellbeing` payload is required rather than a status string, so the
 * component cannot render without the counts and thresholds behind it — the
 * same enforcement `ChartFrame` applies to `computedFrom`.
 *
 * It describes observations, never states. "More low-valence readings than
 * usual this week", never "you are distressed" — the same discipline as "the
 * channels disagree" rather than "you are concealing something".
 */
export function DistressIndicator({ wellbeing }: { wellbeing: Wellbeing }) {
  const {
    status,
    days_with_data,
    low_valence_days,
    conflict_days,
    sustained_low_valence,
    sustained_conflict,
    window_days,
    sustained_days_required,
    minimum_days,
    low_valence_threshold,
    low_valence_share_threshold,
  } = wellbeing;

  const headline =
    status === "insufficient_data"
      ? "Not enough recorded days yet"
      : status === "steady"
        ? "Nothing stood out this week"
        : "Some readings stood out this week";

  return (
    <section className={`distress distress-${status}`} aria-labelledby="wellbeing-heading">
      <h2 id="wellbeing-heading">{headline}</h2>

      {status === "insufficient_data" ? (
        <p className="distress-lead">
          {days_with_data} of the {minimum_days} days needed have enough recorded readings. This is
          not a low result — there is genuinely nothing measured yet.
        </p>
      ) : status === "observations" ? (
        <ul className="distress-observations">
          {sustained_low_valence && (
            <li>
              More low-valence readings than usual on <strong>{low_valence_days}</strong> of the
              last {window_days} days.
            </li>
          )}
          {sustained_conflict && (
            <li>
              Your channels disagreed with each other on <strong>{conflict_days}</strong> of the
              last {window_days} days.
            </li>
          )}
        </ul>
      ) : (
        <p className="distress-lead">
          Across {days_with_data} recorded days, neither observation reached the point where it
          would be worth mentioning.
        </p>
      )}

      {/* Always rendered: the composite is meaningless without them. */}
      <dl className="distress-components">
        <div>
          <dt>Days with enough data</dt>
          <dd>
            {days_with_data} of {window_days}
          </dd>
        </div>
        <div>
          <dt>Low-valence days</dt>
          <dd>{low_valence_days}</dd>
        </div>
        <div>
          <dt>Conflict days</dt>
          <dd>{conflict_days}</dd>
        </div>
      </dl>

      <p className="distress-computed-from">
        A day counts as low-valence when at least{" "}
        {Math.round(low_valence_share_threshold * 100)}% of its combined readings fall below a
        valence of {low_valence_threshold.toFixed(2)}. Something is only called out when it holds on{" "}
        {sustained_days_required} or more of the last {window_days} days — a single day never
        counts. These thresholds are provisional and have not yet been derived from labelled data.
      </p>

      <p className="distress-caveat">
        These are observations about recordings, not statements about you. Reflect does not
        diagnose, does not grade, and is not a clinical assessment.
      </p>
    </section>
  );
}
