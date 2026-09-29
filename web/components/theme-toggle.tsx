"use client";

import { Monitor, Moon, Sun } from "lucide-react";
import { useEffect, useState } from "react";
import { flushSync } from "react-dom";
import { THEME_KEY } from "@/lib/theme";
import { cn } from "@/lib/utils";

export type ThemeChoice = "light" | "dark" | "system";
const KEY = THEME_KEY;
const ORDER: ThemeChoice[] = ["light", "dark", "system"];

function stored(): ThemeChoice {
  try {
    const v = localStorage.getItem(KEY);
    return v === "light" || v === "dark" ? v : "system";
  } catch {
    return "system";
  }
}

function resolve(choice: ThemeChoice): "light" | "dark" {
  if (choice !== "system") return choice;
  return window.matchMedia("(prefers-color-scheme: dark)").matches ? "dark" : "light";
}

function apply(choice: ThemeChoice) {
  document.documentElement.dataset.theme = resolve(choice);
}

const ICON = { light: Sun, dark: Moon, system: Monitor };
const LABEL = { light: "Light", dark: "Dark", system: "System" };

/** Light / dark / system. The new theme spreads as a circle from the button where the browser supports it. */
export function ThemeToggle() {
  const [choice, setChoice] = useState<ThemeChoice>("system");

  useEffect(() => {
    // Read the stored choice after mount (the server can't know it); the pre-paint script already applied it.
    const c = stored();
    const id = requestAnimationFrame(() => setChoice(c));
    const mq = window.matchMedia("(prefers-color-scheme: dark)");
    const onSystem = () => {
      if (stored() === "system") apply("system");
    };
    mq.addEventListener("change", onSystem);
    return () => {
      cancelAnimationFrame(id);
      mq.removeEventListener("change", onSystem);
    };
  }, []);

  const choose = (next: ThemeChoice, e: React.MouseEvent) => {
    try {
      if (next === "system") localStorage.removeItem(KEY);
      else localStorage.setItem(KEY, next);
    } catch {
      /* storage blocked: the choice still applies for this page */
    }
    const change = () => {
      flushSync(() => setChoice(next));
      apply(next);
    };
    const doc = document as Document & { startViewTransition?: (cb: () => void) => { ready: Promise<void> } };
    const reduced = window.matchMedia("(prefers-reduced-motion: reduce)").matches;
    if (!doc.startViewTransition || reduced || resolve(next) === document.documentElement.dataset.theme) {
      change();
      return;
    }
    const x = e.clientX;
    const y = e.clientY;
    const r = Math.hypot(Math.max(x, innerWidth - x), Math.max(y, innerHeight - y));
    const root = document.documentElement;
    root.classList.add("theme-switching");
    const t = doc.startViewTransition(change);
    t.ready
      .then(() =>
        root
          .animate(
            { clipPath: [`circle(0px at ${x}px ${y}px)`, `circle(${r}px at ${x}px ${y}px)`] },
            { duration: 650, easing: "cubic-bezier(0.16, 1, 0.3, 1)", pseudoElement: "::view-transition-new(root)" },
          )
          .finished.finally(() => root.classList.remove("theme-switching")),
      )
      .catch(() => root.classList.remove("theme-switching"));
  };

  return (
    <div role="radiogroup" aria-label="Colour theme" className="flex items-center gap-0.5 rounded-full border p-0.5">
      {ORDER.map((c) => {
        const Icon = ICON[c];
        const on = c === choice;
        return (
          <button
            key={c}
            role="radio"
            aria-checked={on}
            aria-label={LABEL[c]}
            title={LABEL[c]}
            onClick={(e) => choose(c, e)}
            className={cn(
              "flex h-7 w-7 items-center justify-center rounded-full transition-all duration-300",
              on ? "bg-foreground text-background" : "text-muted-foreground hover:text-foreground",
            )}
          >
            <Icon className="h-3.5 w-3.5" />
          </button>
        );
      })}
    </div>
  );
}
