import type { Metadata } from "next";
import { Geist, Geist_Mono, Instrument_Serif } from "next/font/google";
import { SiteHeader } from "@/components/site-header";
import { THEME_SCRIPT } from "@/lib/theme";
import { TooltipProvider } from "@/components/ui/tooltip";
import "./globals.css";

const geistSans = Geist({ variable: "--font-geist-sans", subsets: ["latin"] });
const geistMono = Geist_Mono({ variable: "--font-geist-mono", subsets: ["latin"] });
const display = Instrument_Serif({
  variable: "--font-display",
  subsets: ["latin"],
  weight: "400",
  style: ["normal", "italic"],
});

export const metadata: Metadata = {
  title: "EdgeMemory",
  description: "Exception copilot for procurement: learns where the happy path breaks, and how your people fixed it.",
};

export default function RootLayout({ children }: LayoutProps<"/">) {
  return (
    <html
      lang="en"
      className={`${geistSans.variable} ${geistMono.variable} ${display.variable} h-full antialiased`}
      suppressHydrationWarning
    >
      <head>
        {/* Applies the saved theme before first paint (no flash). */}
        <script dangerouslySetInnerHTML={{ __html: THEME_SCRIPT }} />
      </head>
      <body className="flex min-h-full flex-col">
        <TooltipProvider delayDuration={150}>
          <SiteHeader />
          <main className="mx-auto w-full max-w-6xl flex-1 px-4 pb-16 md:px-6">{children}</main>
          <footer className="mt-10 overflow-hidden border-t">
            <div className="mx-auto flex max-w-6xl flex-col gap-6 px-4 pt-10 md:px-6">
              <div className="grid gap-4 text-sm text-muted-foreground md:grid-cols-3">
                <p>
                  <strong className="text-foreground">Synthetic data.</strong> Kaveri Precision Components, its
                  people, vendors and cases are fictional.
                </p>
                <p>EdgeMemory recommends; a human always decides. It never releases a payment.</p>
                <p>Memory by Hindsight. Built for HackwithHyderabad 3.0.</p>
              </div>
              <div className="select-none font-display text-[22vw] leading-[0.8] tracking-tight text-foreground/[0.06] md:text-[15rem]">
                Edge<span className="italic">Memory</span>
              </div>
            </div>
          </footer>
        </TooltipProvider>
      </body>
    </html>
  );
}
