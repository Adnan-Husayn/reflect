import { render, screen } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { describe, expect, it, vi } from "vitest";
import { WithdrawData } from "./WithdrawData";

const receipt = {
  deleted_sessions: 3,
  deleted_readings: 412,
  deleted_fused_readings: 96,
  deleted_checkins: 2,
};

describe("WithdrawData", () => {
  it("asks for confirmation before calling the endpoint", async () => {
    const user = userEvent.setup();
    const onWithdraw = vi.fn().mockResolvedValue(receipt);
    render(<WithdrawData onWithdraw={onWithdraw} />);

    await user.click(screen.getByRole("button", { name: "Delete my data" }));

    expect(onWithdraw).not.toHaveBeenCalled();
    expect(screen.getByText(/This deletes every check-in/)).toBeInTheDocument();
    expect(screen.getByRole("button", { name: "Delete everything" })).toBeInTheDocument();
  });

  it("deletes only after the second confirmation", async () => {
    const user = userEvent.setup();
    const onWithdraw = vi.fn().mockResolvedValue(receipt);
    render(<WithdrawData onWithdraw={onWithdraw} />);

    await user.click(screen.getByRole("button", { name: "Delete my data" }));
    await user.click(screen.getByRole("button", { name: "Delete everything" }));

    expect(onWithdraw).toHaveBeenCalledOnce();
  });

  it("can be cancelled without deleting anything", async () => {
    const user = userEvent.setup();
    const onWithdraw = vi.fn().mockResolvedValue(receipt);
    render(<WithdrawData onWithdraw={onWithdraw} />);

    await user.click(screen.getByRole("button", { name: "Delete my data" }));
    await user.click(screen.getByRole("button", { name: "Cancel" }));

    expect(onWithdraw).not.toHaveBeenCalled();
    expect(screen.getByRole("button", { name: "Delete my data" })).toBeInTheDocument();
  });

  it("shows a receipt of what was removed", async () => {
    const user = userEvent.setup();
    render(<WithdrawData onWithdraw={vi.fn().mockResolvedValue(receipt)} />);

    await user.click(screen.getByRole("button", { name: "Delete my data" }));
    await user.click(screen.getByRole("button", { name: "Delete everything" }));

    expect(await screen.findByText("Your data has been deleted")).toBeInTheDocument();
    expect(screen.getByRole("status")).toHaveTextContent(
      "Removed 3 sessions, 412 channel readings, 96 combined readings and 2 check-ins.",
    );
  });

  it("says plainly that it cannot be undone", () => {
    render(<WithdrawData onWithdraw={vi.fn()} />);
    expect(screen.getByText(/This cannot be undone/)).toBeInTheDocument();
  });

  it("reports a failure instead of implying the data is gone", async () => {
    const user = userEvent.setup();
    render(<WithdrawData onWithdraw={vi.fn().mockRejectedValue(new Error("Deletion failed."))} />);

    await user.click(screen.getByRole("button", { name: "Delete my data" }));
    await user.click(screen.getByRole("button", { name: "Delete everything" }));

    expect(await screen.findByRole("alert")).toHaveTextContent("Deletion failed.");
    expect(screen.queryByText("Your data has been deleted")).not.toBeInTheDocument();
  });
});
