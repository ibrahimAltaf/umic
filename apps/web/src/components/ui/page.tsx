import Link from "next/link";
import { cn } from "@/lib/utils";

export function PageHeader({
  eyebrow,
  title,
  description,
  actions,
  className,
}: {
  eyebrow?: string;
  title: string;
  description?: string;
  actions?: React.ReactNode;
  className?: string;
}) {
  return (
    <div
      className={cn(
        "flex flex-wrap items-end justify-between gap-4 animate-fade-up",
        className,
      )}
    >
      <div className="min-w-0 max-w-2xl">
        {eyebrow ? <p className="umic-eyebrow">{eyebrow}</p> : null}
        <h1 className="umic-title mt-1">{title}</h1>
        {description ? (
          <p className="mt-2 text-sm leading-relaxed text-muted-foreground">{description}</p>
        ) : null}
      </div>
      {actions ? <div className="flex flex-wrap items-center gap-2">{actions}</div> : null}
    </div>
  );
}

export function EmptyState({
  title,
  description,
  action,
}: {
  title: string;
  description: string;
  action?: React.ReactNode;
}) {
  return (
    <div className="umic-panel flex flex-col items-center justify-center px-6 py-16 text-center">
      <div className="mb-4 h-12 w-12 rounded-full bg-accent/80 ring-1 ring-border" />
      <h3 className="font-display text-lg font-semibold">{title}</h3>
      <p className="mt-2 max-w-md text-sm text-muted-foreground">{description}</p>
      {action ? <div className="mt-5">{action}</div> : null}
    </div>
  );
}

export function Panel({
  children,
  className,
  title,
  action,
}: {
  children: React.ReactNode;
  className?: string;
  title?: string;
  action?: React.ReactNode;
}) {
  return (
    <section className={cn("umic-panel", className)}>
      {title ? (
        <div className="flex items-center justify-between gap-3 border-b border-border/70 px-5 py-3.5">
          <h3 className="text-sm font-semibold tracking-tight">{title}</h3>
          {action}
        </div>
      ) : null}
      <div className={title ? "p-5" : undefined}>{children}</div>
    </section>
  );
}

export function StatTile({
  label,
  value,
  hint,
  href,
  tone = "default",
}: {
  label: string;
  value: React.ReactNode;
  hint?: string;
  href?: string;
  tone?: "default" | "warn" | "ok" | "signal";
}) {
  const tones = {
    default: "from-primary/10 via-transparent to-transparent",
    warn: "from-amber-500/15 via-transparent to-transparent",
    ok: "from-emerald-500/15 via-transparent to-transparent",
    signal: "from-signal/25 via-transparent to-transparent",
  };
  const inner = (
    <div
      className={cn(
        "umic-panel relative overflow-hidden p-5 transition hover:-translate-y-0.5 hover:shadow-lift",
        href && "cursor-pointer",
      )}
    >
      <div
        className={cn(
          "pointer-events-none absolute inset-0 bg-gradient-to-br",
          tones[tone],
        )}
      />
      <p className="relative text-xs font-medium uppercase tracking-wide text-muted-foreground">
        {label}
      </p>
      <p className="relative mt-3 font-display text-3xl font-semibold tracking-tight">{value}</p>
      {hint ? (
        <p className="relative mt-2 text-xs text-muted-foreground">{hint}</p>
      ) : null}
    </div>
  );
  return href ? <Link href={href}>{inner}</Link> : inner;
}

export function QuickLink({
  href,
  label,
  detail,
}: {
  href: string;
  label: string;
  detail: string;
}) {
  return (
    <Link
      href={href}
      className="group flex items-start justify-between gap-3 rounded-md border border-transparent px-3 py-2.5 transition hover:border-border hover:bg-muted/50"
    >
      <div>
        <p className="text-sm font-medium group-hover:text-primary">{label}</p>
        <p className="text-xs text-muted-foreground">{detail}</p>
      </div>
      <span className="mt-0.5 text-muted-foreground transition group-hover:translate-x-0.5 group-hover:text-primary">
        →
      </span>
    </Link>
  );
}
