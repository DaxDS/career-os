import type { Metadata } from "next";
import { getLocale } from "next-intl/server";
import { DM_Sans, Fraunces } from "next/font/google";
import { ThemeProvider } from "@/components/theme-provider";
import "./globals.css";

const dmSans = DM_Sans({ subsets: ["latin"], variable: "--font-sans" });
const fraunces = Fraunces({ subsets: ["latin"], variable: "--font-display" });
export const metadata: Metadata = {
  title: "CareerOS — Job search copilot for Canada",
  description:
    "Every job mapped to NOC codes, wages, and your immigration pathway. Built for newcomers, PGWP holders, and PR-track workers.",
};

const themeInitScript = `(function(){try{var k='careeros-theme';var t=localStorage.getItem(k);if(t==='light'){document.documentElement.classList.remove('dark')}else if(t==='system'){var d=window.matchMedia('(prefers-color-scheme: dark)').matches;document.documentElement.classList.toggle('dark',d)}else{document.documentElement.classList.add('dark')}}catch(e){document.documentElement.classList.add('dark')}})()`;

export default async function RootLayout({
  children,
}: Readonly<{
  children: React.ReactNode;
}>) {
  const locale = await getLocale();

  return (
    <html lang={locale} className={`dark ${dmSans.variable} ${fraunces.variable}`} suppressHydrationWarning>
      <head>
        <script dangerouslySetInnerHTML={{ __html: themeInitScript }} />
      </head>
      <body className={`${dmSans.className} font-sans`}>
        <ThemeProvider
          attribute="class"
          defaultTheme="dark"
          enableSystem
          storageKey="careeros-theme"
          disableTransitionOnChange
        >
          {children}
        </ThemeProvider>
      </body>
    </html>
  );
}
