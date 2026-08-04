"use client";

import { useEffect } from "react";

/**
 * Route-level error boundary.
 *
 * Without this, any unhandled server or render error shows Next.js's raw
 * "Application error: a server-side exception has occurred" screen with a digest
 * string and no way back. That is what a paying customer would have seen.
 */
export default function AppError({
  error,
  reset,
}: {
  error: Error & { digest?: string };
  reset: () => void;
}) {
  useEffect(() => {
    console.error("[app error]", error.message, error.digest ?? "");
  }, [error]);

  return (
    <div className="flex min-h-[60vh] flex-col items-center justify-center gap-4 px-4 text-center">
      <h1 className="text-2xl font-bold">Something went wrong</h1>
      <p className="max-w-md text-sm text-muted-foreground">
        This one is on us, not you. Nothing you entered has been lost — try again, and if it keeps
        happening let us know.
      </p>
      {error.digest && (
        <p className="text-xs text-muted-foreground">
          Reference: <code className="font-mono">{error.digest}</code>
        </p>
      )}
      <div className="flex flex-wrap justify-center gap-3">
        <button
          onClick={reset}
          className="inline-flex h-10 items-center rounded-md bg-primary px-4 text-sm font-medium text-primary-foreground"
        >
          Try again
        </button>
        <a
          href="/dashboard"
          className="inline-flex h-10 items-center rounded-md border border-input px-4 text-sm font-medium"
        >
          Back to dashboard
        </a>
      </div>
    </div>
  );
}
