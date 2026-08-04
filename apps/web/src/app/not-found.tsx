import Link from "next/link";

/** Branded 404. The default was Next.js's bare "This page could not be found." */
export default function NotFound() {
  return (
    <div className="flex min-h-[60vh] flex-col items-center justify-center gap-4 px-4 text-center">
      <p className="text-sm font-medium text-muted-foreground">404</p>
      <h1 className="text-2xl font-bold">We couldn&apos;t find that page</h1>
      <p className="max-w-md text-sm text-muted-foreground">
        The link may be out of date, or the page may have moved.
      </p>
      <div className="flex flex-wrap justify-center gap-3">
        <Link
          href="/"
          className="inline-flex h-10 items-center rounded-md bg-primary px-4 text-sm font-medium text-primary-foreground"
        >
          Go home
        </Link>
        <Link
          href="/pathways"
          className="inline-flex h-10 items-center rounded-md border border-input px-4 text-sm font-medium"
        >
          My PR report
        </Link>
      </div>
    </div>
  );
}
