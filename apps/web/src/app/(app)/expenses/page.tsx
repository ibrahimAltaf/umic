"use client";

import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { useState } from "react";
import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import { PageHeader } from "@/components/ui/page";
import { apiGet, apiSend } from "@/lib/api-client";

type MatterOpt = { id: string; name: string; matter_number: string };
type Expense = {
  id: string;
  matter_name?: string;
  vendor?: string;
  amount: number;
  category: string;
  approval_status: string;
  invoice_date?: string;
};
type Mileage = {
  id: string;
  matter_name?: string;
  activity_date: string;
  origin?: string;
  destination?: string;
  miles: number;
  mileage_amount: number;
  approval_status: string;
};

export default function ExpensesPage() {
  const qc = useQueryClient();
  const [tab, setTab] = useState<"expenses" | "mileage">("expenses");
  const [expenseForm, setExpenseForm] = useState({
    matter_id: "",
    amount: "",
    vendor: "",
    category: "general",
    notes: "",
  });
  const [mileageForm, setMileageForm] = useState({
    matter_id: "",
    activity_date: new Date().toISOString().slice(0, 10),
    miles: "",
    origin: "",
    destination: "",
  });

  const matters = useQuery({
    queryKey: ["matters-opts"],
    queryFn: () => apiGet<{ items: MatterOpt[] }>("/api/v1/matters?page_size=100"),
  });
  const expenses = useQuery({
    queryKey: ["expenses"],
    queryFn: () => apiGet<{ items: Expense[]; total: number }>("/api/v1/expenses?page_size=50"),
  });
  const mileage = useQuery({
    queryKey: ["mileage"],
    queryFn: () => apiGet<{ items: Mileage[]; total: number }>("/api/v1/mileage?page_size=50"),
  });

  const createExpense = useMutation({
    mutationFn: () =>
      apiSend("/api/v1/expenses", "POST", {
        matter_id: expenseForm.matter_id,
        amount: Number(expenseForm.amount),
        vendor: expenseForm.vendor || null,
        category: expenseForm.category,
        notes: expenseForm.notes || null,
      }),
    onSuccess: () => {
      qc.invalidateQueries({ queryKey: ["expenses"] });
      setExpenseForm((f) => ({ ...f, amount: "", vendor: "", notes: "" }));
    },
  });
  const createMileage = useMutation({
    mutationFn: () =>
      apiSend("/api/v1/mileage", "POST", {
        matter_id: mileageForm.matter_id,
        activity_date: mileageForm.activity_date,
        miles: Number(mileageForm.miles),
        origin: mileageForm.origin || null,
        destination: mileageForm.destination || null,
      }),
    onSuccess: () => {
      qc.invalidateQueries({ queryKey: ["mileage"] });
      setMileageForm((f) => ({ ...f, miles: "", origin: "", destination: "" }));
    },
  });
  const decideExpense = useMutation({
    mutationFn: ({ id, approve }: { id: string; approve: boolean }) =>
      apiSend(`/api/v1/expenses/${id}/${approve ? "approve" : "reject"}`, "POST"),
    onSuccess: () => qc.invalidateQueries({ queryKey: ["expenses"] }),
  });
  const decideMileage = useMutation({
    mutationFn: ({ id, approve }: { id: string; approve: boolean }) =>
      apiSend(`/api/v1/mileage/${id}/${approve ? "approve" : "reject"}`, "POST"),
    onSuccess: () => qc.invalidateQueries({ queryKey: ["mileage"] }),
  });

  const matterOptions = matters.data?.items ?? [];

  return (
    <div className="space-y-6">
      <PageHeader
        eyebrow="Finance"
        title="Expenses & mileage"
        description="Capture costs and trips, approve them, then export T&E from a matter file."
      />

      <div className="flex gap-2">
        <button
          className={`rounded-full border px-3.5 py-1.5 text-sm font-medium transition ${
            tab === "expenses"
              ? "border-primary bg-primary text-primary-foreground"
              : "border-border bg-card/80 text-muted-foreground"
          }`}
          onClick={() => setTab("expenses")}
        >
          Expenses
        </button>
        <button
          className={`rounded-full border px-3.5 py-1.5 text-sm font-medium transition ${
            tab === "mileage"
              ? "border-primary bg-primary text-primary-foreground"
              : "border-border bg-card/80 text-muted-foreground"
          }`}
          onClick={() => setTab("mileage")}
        >
          Mileage
        </button>
      </div>

      {tab === "expenses" ? (
        <>
          <form
            className="grid gap-3 rounded-lg border p-4 md:grid-cols-2 lg:grid-cols-3"
            onSubmit={(e) => {
              e.preventDefault();
              createExpense.mutate();
            }}
          >
            <div>
              <Label>Matter</Label>
              <select
                className="mt-1 w-full rounded-md border bg-background px-3 py-2 text-sm"
                value={expenseForm.matter_id}
                onChange={(e) => setExpenseForm({ ...expenseForm, matter_id: e.target.value })}
                required
              >
                <option value="">Select…</option>
                {matterOptions.map((m) => (
                  <option key={m.id} value={m.id}>
                    {m.matter_number} — {m.name}
                  </option>
                ))}
              </select>
            </div>
            <div>
              <Label>Amount</Label>
              <Input
                type="number"
                step="0.01"
                required
                value={expenseForm.amount}
                onChange={(e) => setExpenseForm({ ...expenseForm, amount: e.target.value })}
              />
            </div>
            <div>
              <Label>Vendor</Label>
              <Input
                value={expenseForm.vendor}
                onChange={(e) => setExpenseForm({ ...expenseForm, vendor: e.target.value })}
              />
            </div>
            <div className="md:col-span-2">
              <Label>Notes</Label>
              <Input
                value={expenseForm.notes}
                onChange={(e) => setExpenseForm({ ...expenseForm, notes: e.target.value })}
              />
            </div>
            <div className="flex items-end">
              <Button type="submit" disabled={createExpense.isPending}>
                Add expense
              </Button>
            </div>
            {createExpense.error ? (
              <p className="text-sm text-destructive md:col-span-3">
                {(createExpense.error as Error).message}
              </p>
            ) : null}
          </form>

          <Table>
            {(expenses.data?.items ?? []).map((e) => (
              <tr key={e.id} className="border-b last:border-0">
                <td className="px-4 py-3">{e.matter_name}</td>
                <td className="px-4 py-3">{e.vendor || "—"}</td>
                <td className="px-4 py-3">${e.amount.toFixed(2)}</td>
                <td className="px-4 py-3">
                  <Badge tone={e.approval_status === "pending" ? "warning" : "success"}>
                    {e.approval_status}
                  </Badge>
                </td>
                <td className="px-4 py-3">
                  {e.approval_status === "pending" ? (
                    <div className="flex gap-2">
                      <button
                        className="text-xs underline"
                        onClick={() => decideExpense.mutate({ id: e.id, approve: true })}
                      >
                        Approve
                      </button>
                      <button
                        className="text-xs underline"
                        onClick={() => decideExpense.mutate({ id: e.id, approve: false })}
                      >
                        Reject
                      </button>
                    </div>
                  ) : (
                    "—"
                  )}
                </td>
              </tr>
            ))}
          </Table>
        </>
      ) : (
        <>
          <form
            className="grid gap-3 rounded-lg border p-4 md:grid-cols-2 lg:grid-cols-3"
            onSubmit={(e) => {
              e.preventDefault();
              createMileage.mutate();
            }}
          >
            <div>
              <Label>Matter</Label>
              <select
                className="mt-1 w-full rounded-md border bg-background px-3 py-2 text-sm"
                value={mileageForm.matter_id}
                onChange={(e) => setMileageForm({ ...mileageForm, matter_id: e.target.value })}
                required
              >
                <option value="">Select…</option>
                {matterOptions.map((m) => (
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
                value={mileageForm.activity_date}
                onChange={(e) => setMileageForm({ ...mileageForm, activity_date: e.target.value })}
              />
            </div>
            <div>
              <Label>Miles</Label>
              <Input
                type="number"
                step="0.1"
                required
                value={mileageForm.miles}
                onChange={(e) => setMileageForm({ ...mileageForm, miles: e.target.value })}
              />
            </div>
            <div>
              <Label>Origin</Label>
              <Input
                value={mileageForm.origin}
                onChange={(e) => setMileageForm({ ...mileageForm, origin: e.target.value })}
              />
            </div>
            <div>
              <Label>Destination</Label>
              <Input
                value={mileageForm.destination}
                onChange={(e) => setMileageForm({ ...mileageForm, destination: e.target.value })}
              />
            </div>
            <div className="flex items-end">
              <Button type="submit" disabled={createMileage.isPending}>
                Add mileage
              </Button>
            </div>
          </form>

          <Table cols={["Matter", "Route", "Miles", "Amount", "Status", ""]}>
            {(mileage.data?.items ?? []).map((m) => (
              <tr key={m.id} className="border-b last:border-0">
                <td className="px-4 py-3">{m.matter_name}</td>
                <td className="px-4 py-3">
                  {m.origin || "?"} → {m.destination || "?"}
                </td>
                <td className="px-4 py-3">{m.miles}</td>
                <td className="px-4 py-3">${m.mileage_amount.toFixed(2)}</td>
                <td className="px-4 py-3">
                  <Badge tone={m.approval_status === "pending" ? "warning" : "success"}>
                    {m.approval_status}
                  </Badge>
                </td>
                <td className="px-4 py-3">
                  {m.approval_status === "pending" ? (
                    <div className="flex gap-2">
                      <button
                        className="text-xs underline"
                        onClick={() => decideMileage.mutate({ id: m.id, approve: true })}
                      >
                        Approve
                      </button>
                      <button
                        className="text-xs underline"
                        onClick={() => decideMileage.mutate({ id: m.id, approve: false })}
                      >
                        Reject
                      </button>
                    </div>
                  ) : (
                    "—"
                  )}
                </td>
              </tr>
            ))}
          </Table>
        </>
      )}
    </div>
  );
}

function Table({
  children,
  cols = ["Matter", "Vendor", "Amount", "Status", ""],
}: {
  children: React.ReactNode;
  cols?: string[];
}) {
  return (
    <div className="overflow-hidden rounded-lg border bg-card/90 shadow-panel">
      <table className="w-full text-left text-sm">
        <thead className="border-b bg-muted/40 text-xs uppercase text-muted-foreground">
          <tr>
            {cols.map((c) => (
              <th key={c || "a"} className="px-4 py-3">
                {c}
              </th>
            ))}
          </tr>
        </thead>
        <tbody>{children}</tbody>
      </table>
    </div>
  );
}
