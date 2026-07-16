"use client";

import { useTheme } from "next-themes";
import { useEffect, useState } from "react";
import { useTranslations } from "next-intl";
import { Button } from "@/components/ui/button";
import { cn } from "@/lib/utils";

const THEMES = ["light", "dark", "system"] as const;

export function ThemeSelector() {
  const t = useTranslations("settings.theme");
  const { theme, setTheme } = useTheme();
  const [mounted, setMounted] = useState(false);

  useEffect(() => setMounted(true), []);

  if (!mounted) {
    return <div className="h-10 rounded-md bg-muted animate-pulse" />;
  }

  return (
    <div className="flex flex-wrap gap-2">
      {THEMES.map((value) => (
        <Button
          key={value}
          type="button"
          variant={theme === value ? "default" : "outline"}
          size="sm"
          className={cn("min-w-[5.5rem]", theme === value && "pointer-events-none")}
          onClick={() => setTheme(value)}
        >
          {t(value)}
        </Button>
      ))}
    </div>
  );
}
