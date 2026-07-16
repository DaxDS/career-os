import { DEV_CREDENTIALS } from "@/lib/dev-credentials";

export function DevCredentialsHint({ label }: { label: string }) {
  return (
    <div className="rounded-md border border-amber-200 bg-amber-50 px-3 py-2 text-xs text-amber-950">
      <p className="font-medium">{label}</p>
      <p className="mt-1 font-mono">
        {DEV_CREDENTIALS.email} / {DEV_CREDENTIALS.password}
      </p>
    </div>
  );
}
