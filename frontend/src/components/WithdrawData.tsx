import { useState } from "react";
import type { DeletionReceipt } from "../types/emotion";

interface WithdrawDataProps {
  onWithdraw: () => Promise<DeletionReceipt>;
}

/**
 * Withdrawal, with a confirmation step and a receipt.
 *
 * The receipt matters: a participant who withdraws should be able to see what
 * was removed rather than take it on trust.
 */
export function WithdrawData({ onWithdraw }: WithdrawDataProps) {
  const [isConfirming, setIsConfirming] = useState(false);
  const [isDeleting, setIsDeleting] = useState(false);
  const [receipt, setReceipt] = useState<DeletionReceipt | null>(null);
  const [error, setError] = useState<string | null>(null);

  const withdraw = async () => {
    setIsDeleting(true);
    setError(null);
    try {
      setReceipt(await onWithdraw());
      setIsConfirming(false);
    } catch (withdrawError) {
      setError(
        withdrawError instanceof Error ? withdrawError.message : "Your data could not be deleted.",
      );
    } finally {
      setIsDeleting(false);
    }
  };

  if (receipt) {
    return (
      <section className="withdraw" aria-labelledby="withdraw-heading">
        <h3 id="withdraw-heading">Your data has been deleted</h3>
        <p role="status">
          Removed {receipt.deleted_sessions} session{receipt.deleted_sessions === 1 ? "" : "s"},{" "}
          {receipt.deleted_readings} channel reading
          {receipt.deleted_readings === 1 ? "" : "s"}, {receipt.deleted_fused_readings} combined
          reading{receipt.deleted_fused_readings === 1 ? "" : "s"} and {receipt.deleted_checkins}{" "}
          check-in{receipt.deleted_checkins === 1 ? "" : "s"}.
        </p>
      </section>
    );
  }

  return (
    <section className="withdraw" aria-labelledby="withdraw-heading">
      <h3 id="withdraw-heading">Withdraw your data</h3>
      {error && <p className="status-message status-error" role="alert">{error}</p>}

      {isConfirming ? (
        <>
          <p>
            This deletes every check-in and every recorded session, permanently. It cannot be
            undone.
          </p>
          <div className="button-row">
            <button type="button" className="danger-button" onClick={withdraw} disabled={isDeleting}>
              {isDeleting ? "Deleting…" : "Delete everything"}
            </button>
            <button
              type="button"
              className="secondary-button"
              onClick={() => setIsConfirming(false)}
              disabled={isDeleting}
            >
              Cancel
            </button>
          </div>
        </>
      ) : (
        <>
          <p>Remove every check-in and recorded session. This cannot be undone.</p>
          <button type="button" className="danger-button" onClick={() => setIsConfirming(true)}>
            Delete my data
          </button>
        </>
      )}
    </section>
  );
}
