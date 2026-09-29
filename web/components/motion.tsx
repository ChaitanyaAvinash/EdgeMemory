"use client";

// Motion primitives, CSS-driven (app/globals.css) with small hooks; no animation library. Everything honours
// prefers-reduced-motion: the CSS disables the animations, and the scroll hooks stop moving things.
import { useEffect, useRef, useState } from "react";
import { cn } from "@/lib/utils";

function reducedMotion(): boolean {
  return typeof window !== "undefined" && window.matchMedia("(prefers-reduced-motion: reduce)").matches;
}

/** Fades and lifts its children in when they scroll into view (once). */
export function Reveal({
  children,
  delay = 0,
  className,
  as: Tag = "div",
}: {
  children: React.ReactNode;
  delay?: number;
  className?: string;
  as?: React.ElementType;
}) {
  const ref = useRef<HTMLElement>(null);
  const [inView, setInView] = useState(false);
  useEffect(() => {
    const el = ref.current;
    if (!el) return;
    const io = new IntersectionObserver(
      ([e]) => {
        if (e.isIntersecting) {
          setInView(true);
          io.disconnect();
        }
      },
      { rootMargin: "0px 0px -8% 0px", threshold: 0.08 },
    );
    io.observe(el);
    return () => io.disconnect();
  }, []);
  return (
    <Tag
      ref={ref}
      className={cn("reveal", inView && "is-in", className)}
      style={{ "--d": `${delay}ms` } as React.CSSProperties}
    >
      {children}
    </Tag>
  );
}

/** The page's vertical scroll position, updated once per animation frame. */
export function useScrollY(): number {
  const [y, setY] = useState(0);
  useEffect(() => {
    if (reducedMotion()) return;
    let frame = 0;
    const on = () => {
      cancelAnimationFrame(frame);
      frame = requestAnimationFrame(() => setY(window.scrollY));
    };
    on();
    window.addEventListener("scroll", on, { passive: true });
    return () => {
      cancelAnimationFrame(frame);
      window.removeEventListener("scroll", on);
    };
  }, []);
  return y;
}

/** Moves its children at `speed` times the scroll (negative: against it), for layered depth. */
export function Parallax({
  children,
  speed = 0.2,
  className,
}: {
  children?: React.ReactNode;
  speed?: number;
  className?: string;
}) {
  const y = useScrollY();
  return (
    <div className={className} style={{ transform: `translate3d(0, ${y * speed}px, 0)`, willChange: "transform" }}>
      {children}
    </div>
  );
}

/** Fades and lifts its children out as the page scrolls past `distance` pixels. */
export function FadeOnScroll({
  children,
  distance = 520,
  className,
}: {
  children: React.ReactNode;
  distance?: number;
  className?: string;
}) {
  const y = useScrollY();
  const t = Math.min(1, y / distance);
  return (
    <div
      className={className}
      style={{ opacity: 1 - t, transform: `translate3d(0, ${-t * 60}px, 0)`, filter: `blur(${t * 6}px)` }}
    >
      {children}
    </div>
  );
}

/** A headline whose words rise in one after another. Put emphasis in {italic} segments. */
export function SplitWords({ text, className, start = 0, step = 70 }: { text: string; className?: string; start?: number; step?: number }) {
  const parts = text.split(/(\{[^}]*\})/).filter(Boolean);
  let i = 0;
  return (
    <span className={className}>
      {parts.map((part, pi) => {
        const italic = part.startsWith("{");
        const words = (italic ? part.slice(1, -1) : part).split(/(\s+)/);
        return words.map((w, wi) =>
          /^\s+$/.test(w) || !w ? (
            w
          ) : (
            <span
              key={`${pi}-${wi}`}
              className={cn("word", italic && "italic text-signal")}
              style={{ "--d": `${start + i++ * step}ms` } as React.CSSProperties}
            >
              {w}
            </span>
          ),
        );
      })}
    </span>
  );
}

/** An endless horizontal ticker. */
export function Marquee({ items, className }: { items: React.ReactNode[]; className?: string }) {
  const row = (key: string) => (
    <div key={key} className="flex shrink-0 items-center gap-10 pr-10" aria-hidden={key === "b"}>
      {items.map((it, i) => (
        <span key={i} className="flex items-center gap-10">
          {it}
          <span className="text-signal">✦</span>
        </span>
      ))}
    </div>
  );
  return (
    <div className={cn("marquee overflow-hidden", className)}>
      <div className="marquee-track flex w-max">{[row("a"), row("b")]}</div>
    </div>
  );
}

/** Counts up to `value` when it scrolls into view. It renders the true value until the animation actually runs,
 * so a blocked or skipped animation can never leave a wrong number on screen (the value comes from the API). */
export function CountUp({ value, duration = 1200 }: { value: number; duration?: number }) {
  const ref = useRef<HTMLSpanElement>(null);
  const [shown, setShown] = useState(value);
  useEffect(() => {
    const el = ref.current;
    if (!el || reducedMotion()) return;
    let frame = 0;
    const io = new IntersectionObserver(([e]) => {
      if (!e.isIntersecting) return;
      io.disconnect();
      const t0 = performance.now();
      const tick = (t: number) => {
        const p = Math.min(1, (t - t0) / duration);
        setShown(Math.round(value * (1 - Math.pow(1 - p, 3))));
        if (p < 1) frame = requestAnimationFrame(tick);
      };
      frame = requestAnimationFrame(tick);
    });
    io.observe(el);
    return () => {
      io.disconnect();
      cancelAnimationFrame(frame);
    };
  }, [value, duration]);
  return <span ref={ref} className="tabular-nums">{shown}</span>;
}

/** The editorial page header used on every page. */
export function PageHeader({
  eyebrow,
  title,
  children,
}: {
  eyebrow: string;
  title: string;
  children?: React.ReactNode;
}) {
  return (
    <header className="flex flex-col gap-4 pb-4 pt-6 md:pt-10">
      <Reveal>
        <span className="text-xs uppercase tracking-[0.2em] text-muted-foreground">{eyebrow}</span>
      </Reveal>
      <h1 className="font-display text-5xl leading-[0.95] md:text-7xl">
        <SplitWords text={title} start={80} />
      </h1>
      {children && (
        <Reveal delay={250} className="max-w-2xl text-base text-muted-foreground md:text-lg">
          {children}
        </Reveal>
      )}
    </header>
  );
}
