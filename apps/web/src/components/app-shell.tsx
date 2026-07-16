import { Link, redirect } from "@/i18n/routing";
import { createClient } from "@/lib/supabase/server";
import { Button } from "@/components/ui/button";

const NAV_ITEMS = [
  { href: "/dashboard", label: "Dashboard" },
  { href: "/jobs", label: "Jobs" },
  { href: "/pathways", label: "Pathways" },
  { href: "/queue", label: "Review queue" },
  { href: "/tracker", label: "Tracker" },
  { href: "/profile", label: "Profile" },
  { href: "/activity", label: "Activity" },
  { href: "/settings", label: "Settings" },
];

export async function AppShell({ children }: { children: React.ReactNode }) {
  const supabase = await createClient();
  const {
    data: { user },
  } = await supabase.auth.getUser();

  if (!user) {
    redirect("/login");
  }

  const { data: profile } = await supabase
    .from("profiles")
    .select("onboarding_completed, full_name")
    .eq("id", user.id)
    .single();

  return (
    <div className="flex min-h-screen">
      <aside className="hidden w-56 shrink-0 border-r bg-muted/30 md:block">
        <div className="flex h-16 items-center border-b px-4">
          <Link href="/dashboard" className="font-bold text-primary">
            CareerOS
          </Link>
        </div>
        <nav className="space-y-1 p-3">
          {NAV_ITEMS.map((item) => (
            <Link
              key={item.href}
              href={item.href}
              className="block rounded-md px-3 py-2 text-sm text-muted-foreground hover:bg-accent hover:text-foreground"
            >
              {item.label}
            </Link>
          ))}
        </nav>
      </aside>

      <div className="flex flex-1 flex-col">
        <header className="flex h-16 items-center justify-between border-b px-4 md:px-6">
          <div>
            <p className="text-sm text-muted-foreground">Welcome back</p>
            <p className="font-medium">{profile?.full_name || user.email}</p>
          </div>
          {!profile?.onboarding_completed && (
            <Button asChild size="sm">
              <Link href="/onboarding">Complete onboarding</Link>
            </Button>
          )}
        </header>
        <main className="flex-1 p-4 md:p-6">{children}</main>
      </div>
    </div>
  );
}
