"use client";

import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import Link from "next/link";
import { useState } from "react";
import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import { PageHeader, Panel, StatTile } from "@/components/ui/page";
import { apiGet, apiSend } from "@/lib/api-client";

type Entry = {
  id: string;
  matter_name?: string;
  activity_date: string;
  description: string;
  details?: string;
  time_charge?: number;
  total_amount?: number;
  approval_status: string;
  code?: string;
};

type MatterOpt = {
  id: string;
  name: string;
  matter_number: string;
  billing_classification?: { allows_proposed_billing?: boolean };
};

export default function BillingPage() {
  const qc = useQueryClient();
  const [showCreate, setShowCreate] = useState(false);
  const [form, setForm] = useState({
    matter_id: "",
    activity_date: new Date().toISOString().slice(0, 10),
    description: "",
    time_charge: "",
    code: "",
  });

  const { data, isLoading } = useQuery({
    queryKey: ["billing-entries"],
    queryFn: () => apiGet<{ items: Entry[] }>("/api/v1/billing/entries?page_size=50"),
  });
  const matters = useQuery({
    queryKey: ["matters-billable"],
    queryFn: () => apiGet<{ items: MatterOpt[] }>("/api/v1/matters?page_size=100"),
    enabled: showCreate,
  });
  const billingCodes = useQuery({
    queryKey: ["billing-codes"],
    queryFn: () =>
      apiGet<{ codes: { code: string; description: string }[] }[]>("/api/v1/billing/codes"),
    enabled: showCreate,
  });

  const approve = useMutation({
    mutationFn: (id: string) =>
      apiSend(`/api/v1/billing/entries/${id}/approve`, "POST", {}),
    onSuccess: () => qc.invalidateQueries({ queryKey: ["billing-entries"] }),
  });
  const reject = useMutation({
    mutationFn: (id: string) =>
      apiSend(`/api/v1/billing/entries/${id}/reject`, "POST", { reason: "Rejected in UI" }),
    onSuccess: () => qc.invalidateQueries({ queryKey: ["billing-entries"] }),
  });
  const create = useMutation({
    mutationFn: () =>
      apiSend("/api/v1/billing/entries", "POST", {
        matter_id: form.matter_id,
        activity_date: form.activity_date,
        description: form.description,
        time_charge: form.time_charge ? Number(form.time_charge) : null,
        code: form.code || null,
        is_manual_override: true,
      }),
    onSuccess: () => {
      setForm((f) => ({ ...f, description: "", time_charge: "", code: "" }));
      setShowCreate(false);
      qc.invalidateQueries({ queryKey: ["billing-entries"] });
    },
  });

  const pending = (data?.items ?? []).filter((e) => e.approval_status === "pending");
  const others = (data?.items ?? []).filter((e) => e.approval_status !== "pending");
  const pendingTotal = pending.reduce((s, e) => s + Number(e.total_amount ?? 0), 0);
  const approvedTotal = others
    .filter((e) => e.approval_status === "approved")
    .reduce((s, e) => s + Number(e.total_amount ?? 0), 0);
  const flatCodes = (billingCodes.data ?? []).flatMap((lib) => lib.codes ?? []);

  return (
    <div className="space-y-6">
      <PageHeader
        eyebrow="Finance"
        title="Billing proposals"
        description="Automation proposes — you approve. Only billable matters generate formal entries."
        actions={
          <>
            <Button variant="outline" onClick={() => setShowCreate((v) => !v)}>
              {showCreate ? "Cancel" : "Propose entry"}
            </Button>
            <Button asChild variant="outline">
              <Link href="/matters">Open matters</Link>
            </Button>
          </>
        }
      />

      {showCreate ? (
        <Panel title="Propose billing entry">
          <form
            className="grid gap-3 md:grid-cols-2"
            onSubmit={(e) => {
              e.preventDefault();
              create.mutate();
            }}
          >
            <div className="md:col-span-2">
              <Label>Matter</Label>
              <select
                required
                className="mt-1 w-full rounded-md border bg-background px-3 py-2 text-sm"
                value={form.matter_id}
                onChange={(e) => setForm({ ...form, matter_id: e.target.value })}
              >
                <option value="">Select matter…</option>
                {(matters.data?.items ?? []).map((m) => (
                  <option key={m.id} value={m.id}>
                    {m.matter_number} — {m.name}
                  </option>
                ))}
              </select>
            </div>
            <div>
              <Label>Date</Label>
              <Input
                type="date"
                required
                value={form.activity_date}
                onChange={(e) => setForm({ ...form, activity_date: e.target.value })}
              />
            </div>
            <div>
              <Label>Hours</Label>
              <Input
                type="number"
                step="0.1"
                value={form.time_charge}
                onChange={(e) => setForm({ ...form, time_charge: e.target.value })}
              />
            </div>
            <div className="md:col-span-2">
              <Label>Description</Label>
              <Input
                required
                value={form.description}
                onChange={(e) => setForm({ ...form, description: e.target.value })}
              />
            </div>
            <div>
              <Label>Code (optional)</Label>
              <select
                className="mt-1 w-full rounded-md border bg-background px-3 py-2 text-sm"
                value={form.code}
                onChange={(e) => setForm({ ...form, code: e.target.value })}
              >
                <option value="">None</option>
                {flatCodes.map((c) => (
                  <option key={c.code} value={c.code}>
                    {c.code} — {c.description}
                  </option>
                ))}
              </select>
            </div>
            <div className="flex items-end">
              <Button type="submit" disabled={create.isPending || !form.matter_id}>
                {create.isPending ? "Saving…" : "Propose"}
              </Button>
            </div>
            {create.error ? (
              <p className="text-sm text-destructive md:col-span-2">
                {(create.error as Error).message}
              </p>
            ) : null}
          </form>
        </Panel>
      ) : null}

      <div className="grid gap-3 sm:grid-cols-3">
        <StatTile label="Awaiting review" value={pending.length} tone="warn" />
        <StatTile label="Pending $" value={`$${pendingTotal.toFixed(2)}`} tone="signal" />
        <StatTile label="Approved (listed)" value={`$${approvedTotal.toFixed(2)}`} tone="ok" />
      </div>

      <Panel title={`Awaiting review (${pending.length})`}>
        {isLoading ? (
          <p className="text-sm text-muted-foreground">Loading…</p>
        ) : pending.length === 0 ? (
          <p className="text-sm text-muted-foreground">
            No pending proposals. When automation or manual entries land, they show up here.
          </p>
        ) : (
          <div className="space-y-3">
            {pending.map((e) => (
              <div
                key={e.id}
                className="rounded-lg border bg-gradient-to-br from-amber-500/5 to-transparent p-4"
              >
                <div className="flex flex-wrap items-start justify-between gap-3">
                  <div>
                    <p className="font-medium">{e.description}</p>
                    <p className="mt-1 text-sm text-muted-foreground">
                      {e.matter_name} · {e.activity_date}
                      {e.code ? ` · ${e.code}` : ""}
                    </p>
                    {e.details ? <p className="mt-2 text-sm">{e.details}</p> : null}
                  </div>
                  <div className="text-right">
                    <p className="font-display text-xl font-semibold">
                      ${Number(e.total_amount ?? 0).toFixed(2)}
                    </p>
                    <p className="text-xs text-muted-foreground">{e.time_charge ?? 0}h</p>
                  </div>
                </div>
                <div className="mt-4 flex gap-2">
                  <Button size="sm" onClick={() => approve.mutate(e.id)}>
                    Approve
                  </Button>
                  <Button size="sm" variant="outline" onClick={() => reject.mutate(e.id)}>
                    Reject
                  </Button>
                </div>
              </div>
            ))}
          </div>
        )}
      </Panel>

      <Panel title="Recent decisions">
        <div className="overflow-x-auto">
          <table className="w-full text-left text-sm">
            <thead className="border-b text-xs uppercase text-muted-foreground">
              <tr>
                <th className="py-2 pr-3">Description</th>
                <th className="py-2 pr-3">Matter</th>
                <th className="py-2 pr-3">Amount</th>
                <th className="py-2">Status</th>
              </tr>
            </thead>
            <tbody>
              {others.length === 0 ? (
                <tr>
                  <td colSpan={4} className="py-8 text-center text-muted-foreground">
                    No decisions yet.
                  </td>
                </tr>
              ) : (
                others.map((e) => (
                  <tr key={e.id} className="border-b last:border-0">
                    <td className="py-3 pr-3 font-medium">{e.description}</td>
                    <td className="py-3 pr-3 text-muted-foreground">{e.matter_name}</td>
                    <td className="py-3 pr-3">${Number(e.total_amount ?? 0).toFixed(2)}</td>
                    <td className="py-3">
                      <Badge tone={e.approval_status === "approved" ? "success" : "danger"}>
                        {e.approval_status}
                      </Badge>
                    </td>
                  </tr>
                ))
              )}
            </tbody>
          </table>
        </div>
      </Panel>
    </div>
  );
}
