import { useCallback, useEffect, useMemo, useState } from "react";
import { ConsentGate } from "../components/ConsentGate";
import { EmptyState } from "../components/EmptyState";
import { StatusMessage } from "../components/StatusMessage";
import { SupportInfo } from "../components/SupportInfo";
import { WithdrawData } from "../components/WithdrawData";
import {
  deleteCheckin,
  deleteMyData,
  exportUrl,
  getCheckins,
  getInstrument,
  postCheckin,
} from "../services/api";
import type { CheckInOut, Instrument } from "../types/emotion";

const CONSENT_KEY = "reflect.checkin.consent";
const INSTRUMENTS = ["PHQ-8", "GAD-7"] as const;
type InstrumentCode = (typeof INSTRUMENTS)[number];
/**
 * PHQ-8 asks about the previous two weeks, so daily answers are heavily
 * autocorrelated: more rows, no more information. The form invites a weekly
 * check-in. The backend's one-per-day constraint stays as a backstop so a
 * mis-tapped entry can still be corrected the next day.
 */
const CADENCE_DAYS = 7;

const today = () => new Date().toISOString().slice(0, 10);

function nextDue(latest: CheckInOut | undefined): string | null {
  if (!latest) return null;
  const due = new Date(latest.taken_on);
  due.setDate(due.getDate() + CADENCE_DAYS);
  return due.toISOString().slice(0, 10);
}

const formatDate = (value: string) =>
  new Date(value).toLocaleDateString(undefined, { dateStyle: "medium" });

export function CheckIn() {
  const [code, setCode] = useState<InstrumentCode>("PHQ-8");
  const [instrument, setInstrument] = useState<Instrument | null>(null);
  const [checkins, setCheckins] = useState<CheckInOut[]>([]);
  const [responses, setResponses] = useState<Record<string, number>>({});
  const [hasConsented, setHasConsented] = useState(() => {
    try {
      return localStorage.getItem(CONSENT_KEY) === "true";
    } catch {
      return false;
    }
  });
  const [error, setError] = useState<string | null>(null);
  const [confirmation, setConfirmation] = useState<string | null>(null);
  const [isSubmitting, setIsSubmitting] = useState(false);
  const [isLoading, setIsLoading] = useState(true);

  const load = useCallback(async (which: InstrumentCode) => {
    try {
      const [nextInstrument, nextCheckins] = await Promise.all([
        getInstrument(which),
        getCheckins(),
      ]);
      setInstrument(nextInstrument);
      setCheckins(nextCheckins);
      setError(null);
    } catch (loadError) {
      setError(loadError instanceof Error ? loadError.message : "The check-in is unavailable.");
    } finally {
      setIsLoading(false);
    }
  }, []);

  useEffect(() => {
    void load(code);
  }, [code, load]);

  const answeredAll = useMemo(
    () => instrument !== null && instrument.items.every((item) => item.id in responses),
    [instrument, responses],
  );
  const total = useMemo(
    () => Object.values(responses).reduce((sum, value) => sum + value, 0),
    [responses],
  );

  const accept = () => {
    setHasConsented(true);
    try {
      localStorage.setItem(CONSENT_KEY, "true");
    } catch {
      // A viewer blocking site data simply sees the gate again next visit,
      // which is the safe direction to fail in.
    }
  };

  const remove = async (checkinId: string) => {
    setError(null);
    try {
      await deleteCheckin(checkinId);
      setCheckins((current) => current.filter((entry) => entry.id !== checkinId));
    } catch (removeError) {
      setError(removeError instanceof Error ? removeError.message : "That check-in could not be removed.");
    }
  };

  const submit = async () => {
    if (!instrument || !answeredAll) return;
    setIsSubmitting(true);
    setError(null);
    try {
      // The server recomputes this from the responses and rejects a mismatch,
      // so the value sent here is a checksum rather than the source of truth.
      const saved = await postCheckin({
        taken_on: today(),
        instrument: code,
        responses,
        score: total,
      });
      setCheckins((current) => [saved, ...current]);
      setResponses({});
      setConfirmation(`Check-in recorded. Your score today is ${saved.score} out of ${instrument.max_score}.`);
    } catch (submitError) {
      setError(submitError instanceof Error ? submitError.message : "The check-in could not be saved.");
    } finally {
      setIsSubmitting(false);
    }
  };

  const forInstrument = checkins.filter((entry) => entry.instrument === code);
  const latest = forInstrument[0];
  const due = nextDue(latest);

  return (
    <main className="page-shell">
      <header className="page-header">
        <p className="project-code">PCS26/146</p>
        <h1>Check-in</h1>
        <p>
          A short weekly questionnaire. Its score is compared against the sessions you record, to
          test whether this project&rsquo;s index tracks a validated instrument.
        </p>
      </header>

      {!hasConsented ? (
        <>
          <ConsentGate onAccept={accept} />
          <SupportInfo />
        </>
      ) : (
        <>
          <StatusMessage message={error} />
          {confirmation && <StatusMessage message={confirmation} tone="info" />}

          {isLoading ? (
            <p className="loading-note">Loading the questionnaire…</p>
          ) : instrument ? (
            <section className="checkin-form" aria-labelledby="instrument-heading">
              <div className="instrument-picker" role="group" aria-label="Questionnaire">
                {INSTRUMENTS.map((option) => (
                  <button
                    key={option}
                    type="button"
                    className={option === code ? "range-button active" : "range-button"}
                    aria-pressed={option === code}
                    onClick={() => {
                      setCode(option);
                      setResponses({});
                      setConfirmation(null);
                    }}
                  >
                    {option}
                  </button>
                ))}
              </div>
              <h2 id="instrument-heading">{instrument.name}</h2>
              <p className="instrument-prompt">{instrument.prompt}</p>

              {due && (
                <p className="cadence-note">
                  Last completed {formatDate(latest.taken_on)}. Next one due {formatDate(due)} —
                  weekly is enough, because the questions ask about the previous two weeks.
                </p>
              )}

              <ol className="instrument-items">
                {instrument.items.map((item) => (
                  <li key={item.id}>
                    <fieldset>
                      <legend>{item.text}</legend>
                      <div className="option-row">
                        {instrument.options.map((option) => (
                          <label key={option.value}>
                            <input
                              type="radio"
                              name={item.id}
                              value={option.value}
                              checked={responses[item.id] === option.value}
                              onChange={() =>
                                setResponses((current) => ({ ...current, [item.id]: option.value }))
                              }
                            />
                            <span>{option.label}</span>
                          </label>
                        ))}
                      </div>
                    </fieldset>
                  </li>
                ))}
              </ol>

              <div className="checkin-actions">
                <span className="running-total">
                  {Object.keys(responses).length} of {instrument.items.length} answered
                  {answeredAll ? ` · total ${total} of ${instrument.max_score}` : ""}
                </span>
                <button
                  type="button"
                  className="secondary-button"
                  onClick={submit}
                  disabled={!answeredAll || isSubmitting}
                >
                  {isSubmitting ? "Saving…" : "Submit check-in"}
                </button>
              </div>
            </section>
          ) : (
            <EmptyState title="Questionnaire unavailable">
              The check-in could not be loaded. The rest of Reflect still works.
            </EmptyState>
          )}

          <SupportInfo />

          {checkins.length > 0 && (
            <section className="checkin-history" aria-labelledby="history-heading">
              <h2 id="history-heading">Your check-ins</h2>
              <ul>
                {checkins.map((entry) => (
                  <li key={entry.id}>
                    <span>
                      {formatDate(entry.taken_on)} <span className="mono">{entry.instrument}</span>
                    </span>
                    <span className="checkin-actions-inline">
                      <span className="checkin-score">{entry.score}</span>
                      <button
                        type="button"
                        className="text-button"
                        onClick={() => void remove(entry.id)}
                      >
                        Remove
                      </button>
                    </span>
                  </li>
                ))}
              </ul>
              <p className="checkin-history-note">
                Scores are shown as numbers only. Reflect does not grade them or map them onto
                categories.
              </p>
              <p className="checkin-history-note">
                Take your data with you:{" "}
                <a href={exportUrl("checkins")}>check-ins as CSV</a> ·{" "}
                <a href={exportUrl("sessions")}>sessions as CSV</a>
              </p>
            </section>
          )}

          <WithdrawData onWithdraw={deleteMyData} />
        </>
      )}
    </main>
  );
}
