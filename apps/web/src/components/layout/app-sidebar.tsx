"use client";

import Link from "next/link";
import { usePathname } from "next/navigation";
import {
  Briefcase,
  Building2,
  AlertTriangle,
  ClipboardList,
  FileText,
  LayoutDashboard,
  Mail,
  Receipt,
  ScrollText,
  Search,
  Settings,
  Shield,
  Users,
  Plug,
  Wallet,
  X,
} from "lucide-react";
import { cn } from "@/lib/utils";
import { useMobileNav } from "@/components/layout/mobile-nav";

const groups = [
  {
    label: "Work",
    items: [
      { href: "/dashboard", label: "Dashboard", icon: LayoutDashboard },
      { href: "/search", label: "Search", icon: Search },
      { href: "/matters", label: "Matters", icon: Briefcase },
      { href: "/entities", label: "Entities", icon: Building2 },
      { href: "/review-queue", label: "Review queue", icon: ClipboardList },
      { href: "/discrepancies", label: "Discrepancies", icon: AlertTriangle },
    ],
  },
  {
    label: "Sources",
    items: [
      { href: "/emails", label: "Emails", icon: Mail },
      { href: "/documents", label: "Documents", icon: FileText },
      { href: "/integrations", label: "Integrations", icon: Plug },
    ],
  },
  {
    label: "Finance",
    items: [
      { href: "/billing", label: "Billing", icon: Receipt },
      { href: "/expenses", label: "Expenses", icon: Wallet },
    ],
  },
  {
    label: "Admin",
    items: [
      { href: "/users", label: "Users", icon: Users },
      { href: "/roles", label: "Roles", icon: Shield },
      { href: "/audit", label: "Audit", icon: ScrollText },
      { href: "/settings", label: "Settings", icon: Settings },
    ],
  },
];

export function AppSidebar() {
  const pathname = usePathname();
  const { open, setOpen } = useMobileNav();

  return (
    <aside
      className={cn(
        "fixed inset-y-0 left-0 z-50 flex w-[272px] flex-col border-r border-sidebar-border bg-sidebar text-sidebar-foreground transition-transform md:static md:translate-x-0",
        open ? "translate-x-0" : "-translate-x-full",
      )}
    >
      <div className="relative overflow-hidden border-b border-sidebar-border px-5 py-6">
        <div className="pointer-events-none absolute -right-8 -top-10 h-32 w-32 rounded-full bg-signal/20 blur-2xl" />
        <div className="flex items-start justify-between gap-2">
          <div>
            <p className="text-[10px] font-semibold uppercase tracking-[0.22em] text-sidebar-foreground/55">
              UMIC
            </p>
            <h1 className="mt-1 font-display text-xl font-bold leading-tight tracking-tight">
              Matter
              <span className="block text-signal">Intelligence</span>
            </h1>
          </div>
          <button
            className="rounded-md p-1 text-sidebar-foreground/70 hover:bg-sidebar-accent md:hidden"
            onClick={() => setOpen(false)}
            aria-label="Close menu"
          >
            <X className="h-4 w-4" />
          </button>
        </div>
      </div>

      <nav className="flex-1 space-y-5 overflow-y-auto p-3">
        {groups.map((group) => (
          <div key={group.label}>
            <p className="mb-1.5 px-3 text-[10px] font-semibold uppercase tracking-[0.16em] text-sidebar-foreground/45">
              {group.label}
            </p>
            <div className="space-y-0.5">
              {group.items.map((item) => {
                const active =
                  pathname === item.href || pathname.startsWith(`${item.href}/`);
                const Icon = item.icon;
                return (
                  <Link
                    key={item.href}
                    href={item.href}
                    onClick={() => setOpen(false)}
                    className={cn(
                      "flex items-center gap-3 rounded-md px-3 py-2 text-sm transition-colors",
                      active
                        ? "bg-sidebar-accent text-white shadow-sm ring-1 ring-white/10"
                        : "text-sidebar-foreground/75 hover:bg-sidebar-accent/70 hover:text-white",
                    )}
                  >
                    <Icon className="h-4 w-4 shrink-0 opacity-85" />
                    {item.label}
                  </Link>
                );
              })}
            </div>
          </div>
        ))}
      </nav>

      <div className="border-t border-sidebar-border p-4">
        <div className="rounded-md bg-sidebar-accent/60 px-3 py-2.5">
          <p className="text-[10px] font-semibold uppercase tracking-wider text-sidebar-foreground/50">
            Workspace
          </p>
          <p className="mt-0.5 text-xs text-sidebar-foreground/80">Local MVP · live APIs</p>
        </div>
      </div>
    </aside>
  );
}
