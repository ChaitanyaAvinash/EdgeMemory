"use client";

import Link from "next/link";
import { usePathname } from "next/navigation";
import { useEffect, useState } from "react";
import { ThemeToggle } from "@/components/theme-toggle";
import { cn } from "@/lib/utils";

const NAV: [string, string][] = [
  ["/", "Queue"],
  ["/new", "New request"],
  ["/lessons", "Lessons"],
  ["/benchmark", "Benchmark"],
  ["/demo", "Demo"],
];

// Sticky glass header that tightens once the page scrolls.
export function SiteHeader() {
  const path = usePathname();
  const [scrolled, setScrolled] = useState(false);
  useEffect(() => {
    const on = () => setScrolled(window.scrollY > 24);
    on();
    window.addEventListener("scroll", on, { passive: true });
    return () => window.removeEventListener("scroll", on);
  }, []);
  const active = (href: string) => (href === "/" ? path === "/" || path.startsWith("/cases") : path.startsWith(href));
  return (
    <header
      style={{ viewTransitionName: "site-header" }}
      className={cn(
        "sticky top-0 z-50 transition-all duration-500",
        scrolled ? "border-b bg-background/75 py-2 backdrop-blur-xl" : "border-b border-transparent py-5",
      )}
    >
      <div className="mx-auto flex max-w-6xl items-center gap-x-8 gap-y-2 px-4 md:px-6">
        <Link href="/" className="group flex items-baseline gap-2">
          <span className="font-display text-2xl leading-none">
            Edge<span className="italic text-signal transition-colors duration-500 group-hover:text-foreground">Memory</span>
          </span>
        </Link>
        <nav className="hidden flex-wrap gap-6 text-sm md:flex">
          {NAV.map(([href, label]) => (
            <Link
              key={href}
              href={href}
              aria-current={active(href) ? "page" : undefined}
              className={cn(
                "link-u pb-0.5 transition-colors",
                active(href) ? "text-foreground" : "text-muted-foreground hover:text-foreground",
              )}
            >
              {label}
            </Link>
          ))}
        </nav>
        <span className="ml-auto flex items-center gap-2 text-xs text-muted-foreground">
          <span className="pulse-dot inline-block h-1.5 w-1.5 rounded-full bg-signal" />
          <span className="hidden sm:inline">Kaveri Precision · synthetic data</span>
        </span>
        <ThemeToggle />
      </div>
      <nav className="mx-auto flex max-w-6xl gap-4 overflow-x-auto px-4 pt-2 text-sm md:hidden">
        {NAV.map(([href, label]) => (
          <Link
            key={href}
            href={href}
            aria-current={active(href) ? "page" : undefined}
            className={cn("link-u shrink-0 pb-0.5", active(href) ? "text-foreground" : "text-muted-foreground")}
          >
            {label}
          </Link>
        ))}
      </nav>
    </header>
  );
}
