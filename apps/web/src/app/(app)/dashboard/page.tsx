"use client";

import { useQuery } from "@tanstack/react-query";
import { motion } from "framer-motion";
import Link from "next/link";
import { useEffect, useState } from "react";
import {
  Area,
  AreaChart,
  CartesianGrid,
  Cell,
  Pie,
  PieChart,
  ResponsiveContainer,
  Tooltip,
  XAxis,
  YAxis,
} from "recharts";
import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import { PageHeader, Panel, QuickLink, StatTile } from "@/components/ui/page";
import { apiGet } from "@/lib/api-client";
import { useAuthStore } from "@/stores/auth-store";

type Stats = {
  active_matters: number;
  personal_matters: number;
  billable_matters: number;
  open_review_items: number;
  pending_billing_entries: number;
  approved_billing_total: number;
  entities_count: number;
  integrations_connected: number;
  matters_by_status: { name: string; value: number }[];
  billing_by_month: { month: number; total: number }[];
  review_by_column: { column: string; value: number }[];
};

type ReviewItem = {
  id: string;
  title: string;
  item_type: string;
  priority: string;
  kanban_column: string;
};

const MONTHS = ["", "Jan", "Feb", "Mar", "Apr", "May", "Jun", "Jul", "Aug", "Sep", "Oct", "Nov", "Dec"];
const PIE_COLORS = ["#14532d", "#0f766e", "#c4a035", "#64748b", "#1e3a2f", "#b45309"];

export default function DashboardPage() {
  const user = useAuthStore((s) => s.user);
  const [hello, setHello] = useState("day");
  useEffect(() => {
    setHello(greeting());
  }, []);
  const { data, isLoading, error } = useQuery({
    queryKey: ["dashboard-stats"],
    queryFn: () => apiGet<Stats>("/api/v1/dashboard/stats"),
  });
  const review = useQuery({
    queryKey: ["review-queue-dash"],
    queryFn: () => apiGet<ReviewItem[]>("/api/v1/review-queue"),
  });

  const monthData =
    data?.billing_by_month.map((r) => ({
      name: MONTHS[r.month] ?? String(r.month),
      total: r.total,
    })) ?? [];

  const inbox = (review.data ?? []).filter((i) => i.kanban_column === "inbox").slice(0, 5);

  return (
    <div className="space-y-7">
      <PageHeader
        eyebrow="Command center"
        title={`Good ${hello}, ${user?.first_name ?? "there"}`}
        description="Live view of matters, review backlog, billing, and connected sources — jump straight into work."
        actions={
          <>
            <Button asChild variant="outline">
              <Link href="/integrations">Sync sources</Link>
            </Button>
            <Button asChild>
              <Link href="/matters/new">New matter</Link>
            </Button>
          </>
        }
      />

      {error ? (
        <div className="rounded-md border border-destructive/30 bg-destructive/5 p-4 text-sm text-destructive">
          {(error as Error).message}
        </div>
      ) : null}

      <div className="grid gap-4 sm:grid-cols-2 xl:grid-cols-4">
        <motion.div initial={{ opacity: 0, y: 8 }} animate={{ opacity: 1, y: 0 }}>
          <StatTile
            label="Active matters"
            value={isLoading ? "…" : (data?.active_matters ?? "—")}
            hint="Open files in the system"
            href="/matters"
          />
        </motion.div>
        <motion.div initial={{ opacity: 0, y: 8 }} animate={{ opacity: 1, y: 0 }} transition={{ delay: 0.05 }}>
          <StatTile
            label="Review backlog"
            value={isLoading ? "…" : (data?.open_review_items ?? "—")}
            hint="Unassigned / conflicting items"
            href="/review-queue"
            tone="warn"
          />
        </motion.div>
        <motion.div initial={{ opacity: 0, y: 8 }} animate={{ opacity: 1, y: 0 }} transition={{ delay: 0.1 }}>
          <StatTile
            label="Pending billing"
            value={isLoading ? "…" : (data?.pending_billing_entries ?? "—")}
            hint="Awaiting approval"
            href="/billing"
            tone="signal"
          />
        </motion.div>
        <motion.div initial={{ opacity: 0, y: 8 }} animate={{ opacity: 1, y: 0 }} transition={{ delay: 0.15 }}>
          <StatTile
            label="Approved billing"
            value={
              isLoading
                ? "…"
                : data
                  ? `$${Number(data.approved_billing_total).toLocaleString()}`
                  : "—"
            }
            hint="Year-to-date approved"
            tone="ok"
          />
        </motion.div>
      </div>

      <div className="grid gap-4 xl:grid-cols-5">
        <Panel title="Billing trend" className="xl:col-span-3" action={<Badge tone="success">Live</Badge>}>
          <div className="h-64">
            <ResponsiveContainer width="100%" height="100%">
              <AreaChart data={monthData.length ? monthData : [{ name: "—", total: 0 }]}>
                <defs>
                  <linearGradient id="billingFill" x1="0" y1="0" x2="0" y2="1">
                    <stop offset="0%" stopColor="#0f766e" stopOpacity={0.4} />
                    <stop offset="100%" stopColor="#0f766e" stopOpacity={0} />
                  </linearGradient>
                </defs>
                <CartesianGrid strokeDasharray="3 3" className="stroke-border" />
                <XAxis dataKey="name" tick={{ fontSize: 12 }} />
                <YAxis tick={{ fontSize: 12 }} />
                <Tooltip />
                <Area
                  type="monotone"
                  dataKey="total"
                  stroke="#0f766e"
                  fill="url(#billingFill)"
                  strokeWidth={2}
                />
              </AreaChart>
            </ResponsiveContainer>
          </div>
        </Panel>

        <Panel title="Matters by status" className="xl:col-span-2">
          <div className="h-64">
            <ResponsiveContainer width="100%" height="100%">
              <PieChart>
                <Pie
                  data={
                    data?.matters_by_status?.length
                      ? data.matters_by_status
                      : [{ name: "None", value: 1 }]
                  }
                  dataKey="value"
                  nameKey="name"
                  innerRadius={58}
                  outerRadius={88}
                  paddingAngle={3}
                >
                  {(data?.matters_by_status ?? [{ name: "None", value: 1 }]).map((_, idx) => (
                    <Cell key={idx} fill={PIE_COLORS[idx % PIE_COLORS.length]} />
                  ))}
                </Pie>
                <Tooltip />
              </PieChart>
            </ResponsiveContainer>
          </div>
        </Panel>
      </div>

      <div className="grid gap-4 lg:grid-cols-3">
        <Panel
          title="Needs attention"
          className="lg:col-span-2"
          action={
            <Button asChild size="sm" variant="outline">
              <Link href="/review-queue">Open board</Link>
            </Button>
          }
        >
          {inbox.length ? (
            <ul className="divide-y divide-border/70">
              {inbox.map((item) => (
                <li key={item.id} className="flex items-start justify-between gap-3 py-3 first:pt-0 last:pb-0">
                  <div>
                    <p className="text-sm font-medium">{item.title}</p>
                    <p className="mt-0.5 text-xs text-muted-foreground">{item.item_type}</p>
                  </div>
                  <Badge
                    tone={
                      item.priority === "high"
                        ? "danger"
                        : item.priority === "medium"
                          ? "warning"
                          : "neutral"
                    }
                  >
                    {item.priority}
                  </Badge>
                </li>
              ))}
            </ul>
          ) : (
            <p className="text-sm text-muted-foreground">
              Review inbox is clear. Sync new mail or documents to generate work items.
            </p>
          )}
        </Panel>

        <Panel title="Shortcuts">
          <div className="space-y-1">
            <QuickLink href="/emails" label="Emails" detail="Associate unassigned Gmail" />
            <QuickLink href="/documents" label="Documents" detail="Drive / Dropbox files" />
            <QuickLink href="/expenses" label="Expenses & mileage" detail="Capture costs on matters" />
            <QuickLink href="/billing" label="Billing approvals" detail="Approve proposed entries" />
            <QuickLink
              href="/integrations"
              label="Integrations"
              detail={`${data?.integrations_connected ?? "—"} connected`}
            />
          </div>
        </Panel>
      </div>
    </div>
  );
}

function greeting() {
  const h = new Date().getHours();
  if (h < 12) return "morning";
  if (h < 18) return "afternoon";
  return "evening";
}
