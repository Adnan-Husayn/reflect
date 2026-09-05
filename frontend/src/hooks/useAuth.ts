import { useCallback, useEffect, useState } from "react";
import { getAccount } from "../services/api";
import type { Account } from "../types/emotion";

/**
 * "loading" is a distinct state, not null.
 *
 * Treating an unresolved session as signed-out would flash the login form at
 * someone who is already signed in, on every page load.
 */
export type AuthState = Account | null | "loading";

export function useAuth() {
  const [account, setAccount] = useState<AuthState>("loading");

  const refresh = useCallback(async () => {
    try {
      setAccount(await getAccount());
    } catch {
      setAccount(null);
    }
  }, []);

  useEffect(() => {
    void refresh();
  }, [refresh]);

  return { account, setAccount, refresh };
}
