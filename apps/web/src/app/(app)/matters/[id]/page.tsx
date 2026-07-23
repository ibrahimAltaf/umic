"use client";

import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import Link from "next/link";
import { useParams } from "next/navigation";
import { useEffect, useMemo, useState } from "react";
import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import { PageHeader, Panel, StatTile } from "@/components/ui/page";
import { BusyOverlay } from "@/components/ui/spinner";
import { apiGet, apiSend } from "@/lib/api-client";
import { cn } from "@/lib/utils";

type Matter = {
  id: string;
  matter_number: string;
  name: string;
  claim_number?: string;
  policy_number?: string;
  case_number?: string;
  property_address?: string;
  hourly_rate?: number;
  notes?: string;
  is_personal: boolean;
  is_confidential: boolean;
  is_privileged: boolean;
  status: { name: string; code?: string };
  billing_classification: {
    name: string;
    code: string;
    allows_proposed_billing: boolean;
  };
  matter_type: { name: string };
  aliases: string[];
};

type Overview = {
  totals: {
    approved_billing: number;
    pending_billing: number;
    approved_expenses: number;
    approved_mileage: number;
    grand_total: number;
  };
  counts: {
    emails: number;
    documents: number;
    billing: number;
    expenses: number;
    mileage: number;
    review: number;
    entities: number;
    discrepancies?: number;
  };
  emails: {
    id: string;
    subject?: string;
    sender?: string;
    snippet?: string;
    direction: string;
    received_at?: string;
    link?: string;
    attachment_count: number;
    review_status: string;
  }[];
  documents: {
    id: string;
    file_name: string;
    source_system: string;
    path?: string;
    link?: string;
    modified_at?: string;
    review_status: string;
    has_text: boolean;
  }[];
  billing: {
    id: string;
    activity_date: string;
    description: string;
    time_charge?: number;
    total_amount?: number;
    approval_status: string;
    code?: string;
  }[];
  expenses: {
    id: string;
    vendor?: string;
    amount: number;
    category: string;
    approval_status: string;
    notes?: string;
  }[];
  mileage: {
    id: string;
    activity_date: string;
    origin?: string;
    destination?: string;
    miles: number;
    mileage_amount: number;
    approval_status: string;
  }[];
  review_items: {
    id: string;
    title: string;
    item_type: string;
    priority: string;
    status: string;
    explanation?: string;
  }[];
  entities: {
    id: string;
    relationship_id?: string;
    display_name?: string;
    role: string;
    is_primary: boolean;
  }[];
  unassigned_emails: {
    id: string;
    subject?: string;
    sender?: string;
  }[];
  unassigned_documents: {
    id: string;
    file_name: string;
    source_system: string;
  }[];
  discrepancies?: {
    id: string;
    field_name: string;
    approved_value?: string;
    imported_value?: string;
    source?: string;
    status: string;
    notes?: string;
  }[];
};

type Tab =
  | "overview"
  | "emails"
  | "documents"
  | "billing"
  | "expenses"
  | "entities"
  | "review"
  | "discrepancies";

export default function MatterDetailPage() {
  const params = useParams<{ id: string }>();
  const qc = useQueryClient();
  const [tab, setTab] = useState<Tab>("overview");
  const [expenseForm, setExpenseForm] = useState({ amount: "", vendor: "", notes: "" });
  const [mileageForm, setMileageForm] = useState({
    miles: "",
    origin: "",
    destination: "",
    activity_date: new Date().toISOString().slice(0, 10),
  });
  const [billingForm, setBillingForm] = useState({
    activity_date: new Date().toISOString().slice(0, 10),
    description: "",
    time_charge: "",
    code: "",
  });
  const [entityLink, setEntityLink] = useState({ entity_id: "", role: "insured" });
  const [editingMatter, setEditingMatter] = useState(false);
  const [matterForm, setMatterForm] = useState({
    name: "",
    claim_number: "",
    policy_number: "",
    case_number: "",
    property_address: "",
    hourly_rate: "",
    notes: "",
    status_code: "",
    billing_classification_code: "",
  });

  const { data: m, isLoading, error } = useQuery({
    queryKey: ["matter", params.id],
    queryFn: () => apiGet<Matter>(`/api/v1/matters/${params.id}`),
  });
  const overview = useQuery({
    queryKey: ["matter-overview", params.id],
    queryFn: () => apiGet<Overview>(`/api/v1/matters/${params.id}/overview`),
  });
  const summaryQ = useQuery({
    queryKey: ["matter-summary", params.id],
    queryFn: () =>
      apiGet<{ summary?: string }>(`/api/v1/matters/${params.id}/summary`),
  });
  const entitiesOpts = useQuery({
    queryKey: ["entities-opts"],
    queryFn: () =>
      apiGet<{ items: { id: string; display_name: string }[] }>("/api/v1/entities?page_size=100"),
  });
  const billingCodes = useQuery({
    queryKey: ["billing-codes"],
    queryFn: () =>
      apiGet<{ library: { code: string }; codes: { code: string; description: string }[] }[]>(
        "/api/v1/billing/codes",
      ),
  });
  const matterRef = useQuery({
    queryKey: ["matter-ref"],
    queryFn: () =>
      apiGet<{
        statuses: { code: string; name: string }[];
        billing_classifications: { code: string; name: string }[];
      }>("/api/v1/matters/meta/reference"),
  });
  const integrations = useQuery({
    queryKey: ["integrations"],
    queryFn: () =>
      apiGet<{ provider: string; status: string }[]>("/api/v1/integrations"),
  });

  useEffect(() => {
    if (!m) return;
    setMatterForm({
      name: m.name || "",
      claim_number: m.claim_number || "",
      policy_number: m.policy_number || "",
      case_number: m.case_number || "",
      property_address: m.property_address || "",
      hourly_rate: m.hourly_rate != null ? String(m.hourly_rate) : "",
      notes: m.notes || "",
      status_code: m.status.code || "",
      billing_classification_code: m.billing_classification.code || "",
    });
  }, [m]);

  const invalidate = () => {
    qc.invalidateQueries({ queryKey: ["matter-overview", params.id] });
    qc.invalidateQueries({ queryKey: ["matter-summary", params.id] });
    qc.invalidateQueries({ queryKey: ["emails"] });
    qc.invalidateQueries({ queryKey: ["documents"] });
    qc.invalidateQueries({ queryKey: ["review-queue"] });
  };

  const exportTe = useMutation({
    mutationFn: () =>
      apiSend<{ url: string; rows_exported: number }>(
        `/api/v1/matters/${params.id}/export-te`,
        "POST",
        {},
      ),
    onSuccess: (data) => {
      invalidate();
      if (data.url) window.open(data.url, "_blank");
    },
  });
  const generateSummary = useMutation({
    mutationFn: () =>
      apiSend<{ summary: string }>(`/api/v1/matters/${params.id}/summary`, "POST"),
    onSuccess: () => invalidate(),
  });
  const attachEmail = useMutation({
    mutationFn: (emailId: string) =>
      apiSend(`/api/v1/integrations/emails/${emailId}/associate`, "POST", {
        matter_id: params.id,
      }),
    onSuccess: invalidate,
  });
  const attachDoc = useMutation({
    mutationFn: (docId: string) =>
      apiSend(`/api/v1/integrations/documents/${docId}/associate`, "POST", {
        matter_id: params.id,
      }),
    onSuccess: invalidate,
  });
  const createExpense = useMutation({
    mutationFn: () =>
      apiSend("/api/v1/expenses", "POST", {
        matter_id: params.id,
        amount: Number(expenseForm.amount),
        vendor: expenseForm.vendor || null,
        notes: expenseForm.notes || null,
      }),
    onSuccess: () => {
      setExpenseForm({ amount: "", vendor: "", notes: "" });
      invalidate();
    },
  });
  const createMileage = useMutation({
    mutationFn: () =>
      apiSend("/api/v1/mileage", "POST", {
        matter_id: params.id,
        activity_date: mileageForm.activity_date,
        miles: Number(mileageForm.miles),
        origin: mileageForm.origin || null,
        destination: mileageForm.destination || null,
      }),
    onSuccess: () => {
      setMileageForm((f) => ({ ...f, miles: "", origin: "", destination: "" }));
      invalidate();
    },
  });
  const decideExpense = useMutation({
    mutationFn: ({ id, approve }: { id: string; approve: boolean }) =>
      apiSend(`/api/v1/expenses/${id}/${approve ? "approve" : "reject"}`, "POST"),
    onSuccess: invalidate,
  });
  const decideMileage = useMutation({
    mutationFn: ({ id, approve }: { id: string; approve: boolean }) =>
      apiSend(`/api/v1/mileage/${id}/${approve ? "approve" : "reject"}`, "POST"),
    onSuccess: invalidate,
  });
  const decideBilling = useMutation({
    mutationFn: ({ id, approve }: { id: string; approve: boolean }) =>
      apiSend(`/api/v1/billing/entries/${id}/${approve ? "approve" : "reject"}`, "POST", {}),
    onSuccess: invalidate,
  });
  const createBilling = useMutation({
    mutationFn: () =>
      apiSend("/api/v1/billing/entries", "POST", {
        matter_id: params.id,
        activity_date: billingForm.activity_date,
        description: billingForm.description,
        time_charge: billingForm.time_charge ? Number(billingForm.time_charge) : null,
        code: billingForm.code || null,
        is_manual_override: true,
      }),
    onSuccess: () => {
      setBillingForm((f) => ({ ...f, description: "", time_charge: "", code: "" }));
      invalidate();
      qc.invalidateQueries({ queryKey: ["billing-entries"] });
    },
  });
  const linkEntity = useMutation({
    mutationFn: () =>
      apiSend("/api/v1/relationships", "POST", {
        matter_id: params.id,
        entity_id: entityLink.entity_id,
        role: entityLink.role,
        is_primary: false,
      }),
    onSuccess: () => {
      setEntityLink({ entity_id: "", role: "insured" });
      invalidate();
    },
  });
  const unlinkEntity = useMutation({
    mutationFn: (relationshipId: string) =>
      apiSend(`/api/v1/relationships/${relationshipId}`, "DELETE"),
    onSuccess: invalidate,
  });
  const resolveDiscrepancy = useMutation({
    mutationFn: (id: string) => apiSend(`/api/v1/discrepancies/${id}/resolve`, "POST"),
    onSuccess: invalidate,
  });
  const extractDoc = useMutation({
    mutationFn: (id: string) => apiSend(`/api/v1/documents/${id}/extract`, "POST"),
    onSuccess: invalidate,
  });
  const saveMatter = useMutation({
    mutationFn: () =>
      apiSend(`/api/v1/matters/${params.id}`, "PATCH", {
        name: matterForm.name || undefined,
        claim_number: matterForm.claim_number || null,
        policy_number: matterForm.policy_number || null,
        case_number: matterForm.case_number || null,
        property_address: matterForm.property_address || null,
        hourly_rate: matterForm.hourly_rate ? Number(matterForm.hourly_rate) : null,
        notes: matterForm.notes || null,
        status_code: matterForm.status_code || undefined,
        billing_classification_code: matterForm.billing_classification_code || undefined,
      }),
    onSuccess: () => {
      setEditingMatter(false);
      qc.invalidateQueries({ queryKey: ["matter", params.id] });
      invalidate();
    },
  });

  const o = overview.data;
  const tabs = useMemo(
    () =>
      [
        { id: "overview" as const, label: "Overview", count: null },
        { id: "emails" as const, label: "Emails", count: o?.counts.emails },
        { id: "documents" as const, label: "Documents", count: o?.counts.documents },
        { id: "billing" as const, label: "Billing", count: o?.counts.billing },
        {
          id: "expenses" as const,
          label: "Expenses",
          count: (o?.counts.expenses ?? 0) + (o?.counts.mileage ?? 0),
        },
        { id: "entities" as const, label: "Entities", count: o?.counts.entities },
        { id: "review" as const, label: "Review", count: o?.counts.review },
        {
          id: "discrepancies" as const,
          label: "Discrepancies",
          count: o?.discrepancies?.length ?? o?.counts?.discrepancies ?? 0,
        },
      ] as const,
    [o],
  );

  const flatCodes = (billingCodes.data ?? []).flatMap((lib) => lib.codes ?? []);

  if (isLoading) {
    return (
      <div className="umic-panel p-10 text-center text-sm text-muted-foreground">
        Loading matter file…
      </div>
    );
  }
  if (error) return <p className="text-sm text-destructive">{(error as Error).message}</p>;
  if (!m) return null;

  const billingDisabled = !m.billing_classification.allows_proposed_billing;
  const t = o?.totals;
  const summaryText = generateSummary.data?.summary || summaryQ.data?.summary;
  const sheetsConnected = (integrations.data ?? []).some(
    (c) => c.provider === "google_sheets" && c.status === "connected",
  );

  const busyLabel =
    exportTe.isPending
      ? "Exporting T&E to Sheets…"
      : generateSummary.isPending
        ? "Generating summary…"
        : saveMatter.isPending
          ? "Saving matter…"
          : createBilling.isPending
            ? "Proposing billing entry…"
            : createExpense.isPending
              ? "Saving expense…"
              : createMileage.isPending
                ? "Saving mileage…"
                : linkEntity.isPending
                  ? "Linking entity…"
                  : extractDoc.isPending
                    ? "Extracting document text…"
                    : attachEmail.isPending || attachDoc.isPending
                      ? "Attaching to matter…"
                      : decideBilling.isPending ||
                          decideExpense.isPending ||
                          decideMileage.isPending
                        ? "Updating approval…"
                        : resolveDiscrepancy.isPending
                          ? "Resolving discrepancy…"
                          : null;

  return (
    <div className="relative space-y-6">
      {busyLabel ? <BusyOverlay label={busyLabel} /> : null}
      <PageHeader
        eyebrow={`Matter file · ${m.matter_number}`}
        title={m.name}
        description="Everything for this matter lives here — emails, documents, billing, expenses, entities, review."
        actions={
          <>
            <Button
              variant="outline"
              loading={generateSummary.isPending}
              onClick={() => generateSummary.mutate()}
            >
              {generateSummary.isPending ? "Summarizing…" : "Summary"}
            </Button>
            <Button loading={exportTe.isPending} onClick={() => exportTe.mutate()}>
              {exportTe.isPending ? "Exporting…" : "Export T&E"}
            </Button>
            <Button
              variant="outline"
              disabled={Boolean(busyLabel)}
              onClick={() => setEditingMatter((v) => !v)}
            >
              {editingMatter ? "Cancel edit" : "Edit matter"}
            </Button>
          </>
        }
      />

      {exportTe.error ? (
        <div className="rounded-md border border-amber-500/30 bg-amber-500/10 px-4 py-3 text-sm">
          {(exportTe.error as Error).message}. Connect{" "}
          <Link href="/integrations" className="underline">
            Google Sheets
          </Link>{" "}
          on Integrations, then retry Export T&E.
        </div>
      ) : null}

      {!sheetsConnected ? (
        <div className="rounded-md border px-4 py-3 text-sm text-muted-foreground">
          T&E export needs a connected{" "}
          <Link href="/integrations" className="underline">
            google_sheets
          </Link>{" "}
          account.
        </div>
      ) : null}

      <div className="flex flex-wrap gap-2">
        <Badge>{m.status.name}</Badge>
        <Badge tone={billingDisabled ? "warning" : "success"}>
          {m.billing_classification.name}
        </Badge>
        <Badge>{m.matter_type.name}</Badge>
        {m.claim_number ? <Badge tone="neutral">Claim {m.claim_number}</Badge> : null}
        {m.is_personal ? <Badge tone="danger">Personal</Badge> : null}
      </div>

      <div className="grid gap-3 sm:grid-cols-2 lg:grid-cols-5">
        <StatTile label="Approved billing" value={t ? `$${t.approved_billing.toFixed(2)}` : "—"} tone="ok" />
        <StatTile label="Pending billing" value={t ? `$${t.pending_billing.toFixed(2)}` : "—"} tone="warn" />
        <StatTile label="Expenses" value={t ? `$${t.approved_expenses.toFixed(2)}` : "—"} />
        <StatTile label="Mileage" value={t ? `$${t.approved_mileage.toFixed(2)}` : "—"} />
        <StatTile
          label="Grand total"
          value={t ? `$${t.grand_total.toFixed(2)}` : "—"}
          tone="signal"
          hint={`${o?.counts.emails ?? 0} emails · ${o?.counts.documents ?? 0} docs`}
        />
      </div>

      {/* A–Z matter tabs */}
      <div className="flex flex-wrap gap-1 border-b border-border/80 pb-px">
        {tabs.map((item) => (
          <button
            key={item.id}
            onClick={() => setTab(item.id)}
            className={cn(
              "rounded-t-md px-3.5 py-2.5 text-sm font-medium transition",
              tab === item.id
                ? "bg-card text-foreground shadow-sm ring-1 ring-border"
                : "text-muted-foreground hover:text-foreground",
            )}
          >
            {item.label}
            {item.count != null ? (
              <span className="ml-1.5 rounded-full bg-muted px-1.5 py-0.5 text-[10px] tabular-nums">
                {item.count}
              </span>
            ) : null}
          </button>
        ))}
      </div>

      {tab === "overview" ? (
        <div className="grid gap-4 lg:grid-cols-2">
          <Panel title="Identifiers & notes">
            {editingMatter ? (
              <form
                className="grid gap-3"
                onSubmit={(e) => {
                  e.preventDefault();
                  saveMatter.mutate();
                }}
              >
                <div>
                  <Label>Name</Label>
                  <Input
                    value={matterForm.name}
                    onChange={(e) => setMatterForm({ ...matterForm, name: e.target.value })}
                  />
                </div>
                <div className="grid gap-3 sm:grid-cols-2">
                  <div>
                    <Label>Claim</Label>
                    <Input
                      value={matterForm.claim_number}
                      onChange={(e) =>
                        setMatterForm({ ...matterForm, claim_number: e.target.value })
                      }
                    />
                  </div>
                  <div>
                    <Label>Policy</Label>
                    <Input
                      value={matterForm.policy_number}
                      onChange={(e) =>
                        setMatterForm({ ...matterForm, policy_number: e.target.value })
                      }
                    />
                  </div>
                  <div>
                    <Label>Case</Label>
                    <Input
                      value={matterForm.case_number}
                      onChange={(e) =>
                        setMatterForm({ ...matterForm, case_number: e.target.value })
                      }
                    />
                  </div>
                  <div>
                    <Label>Hourly rate</Label>
                    <Input
                      type="number"
                      step="0.01"
                      value={matterForm.hourly_rate}
                      onChange={(e) =>
                        setMatterForm({ ...matterForm, hourly_rate: e.target.value })
                      }
                    />
                  </div>
                </div>
                <div>
                  <Label>Property</Label>
                  <Input
                    value={matterForm.property_address}
                    onChange={(e) =>
                      setMatterForm({ ...matterForm, property_address: e.target.value })
                    }
                  />
                </div>
                <div className="grid gap-3 sm:grid-cols-2">
                  <div>
                    <Label>Status</Label>
                    <select
                      className="mt-1 w-full rounded-md border bg-background px-3 py-2 text-sm"
                      value={matterForm.status_code}
                      onChange={(e) =>
                        setMatterForm({ ...matterForm, status_code: e.target.value })
                      }
                    >
                      {(matterRef.data?.statuses ?? []).map((s) => (
                        <option key={s.code} value={s.code}>
                          {s.name}
                        </option>
                      ))}
                    </select>
                  </div>
                  <div>
                    <Label>Billing class</Label>
                    <select
                      className="mt-1 w-full rounded-md border bg-background px-3 py-2 text-sm"
                      value={matterForm.billing_classification_code}
                      onChange={(e) =>
                        setMatterForm({
                          ...matterForm,
                          billing_classification_code: e.target.value,
                        })
                      }
                    >
                      {(matterRef.data?.billing_classifications ?? []).map((b) => (
                        <option key={b.code} value={b.code}>
                          {b.name}
                        </option>
                      ))}
                    </select>
                  </div>
                </div>
                <div>
                  <Label>Notes</Label>
                  <Input
                    value={matterForm.notes}
                    onChange={(e) => setMatterForm({ ...matterForm, notes: e.target.value })}
                  />
                </div>
                <Button type="submit" loading={saveMatter.isPending}>
                  {saveMatter.isPending ? "Saving…" : "Save matter"}
                </Button>
                {saveMatter.error ? (
                  <p className="text-sm text-destructive">{(saveMatter.error as Error).message}</p>
                ) : null}
              </form>
            ) : (
              <dl className="space-y-2.5 text-sm">
                <Row label="Claim" value={m.claim_number} />
                <Row label="Policy" value={m.policy_number} />
                <Row label="Case" value={m.case_number} />
                <Row label="Hourly rate" value={m.hourly_rate ? `$${m.hourly_rate}` : undefined} />
                <Row label="Property" value={m.property_address} />
                <Row label="Aliases" value={m.aliases.join(", ") || undefined} />
                <Row label="Notes" value={m.notes} />
              </dl>
            )}
          </Panel>
          <Panel title="Intelligence summary">
            {summaryText ? (
              <pre className="whitespace-pre-wrap font-sans text-sm leading-relaxed text-muted-foreground">
                {summaryText}
              </pre>
            ) : (
              <p className="text-sm text-muted-foreground">
                Generate a summary after linking emails/docs or adding costs.
              </p>
            )}
          </Panel>
          <Panel title="At a glance" className="lg:col-span-2">
            <div className="grid gap-3 sm:grid-cols-2 lg:grid-cols-4 text-sm">
              <Glance label="Emails" value={o?.counts.emails} onClick={() => setTab("emails")} />
              <Glance label="Documents" value={o?.counts.documents} onClick={() => setTab("documents")} />
              <Glance label="Billing lines" value={o?.counts.billing} onClick={() => setTab("billing")} />
              <Glance label="Open review" value={o?.counts.review} onClick={() => setTab("review")} />
            </div>
          </Panel>
        </div>
      ) : null}

      {tab === "emails" ? (
        <div className="space-y-4">
          <Panel title={`Linked emails (${o?.emails.length ?? 0})`}>
            {(o?.emails.length ?? 0) === 0 ? (
              <p className="text-sm text-muted-foreground">
                No emails on this matter yet. Attach from the unassigned pool below, or sync Gmail first.
              </p>
            ) : (
              <ul className="divide-y divide-border/70">
                {o!.emails.map((e) => (
                  <li key={e.id} className="flex flex-col gap-1 py-3 first:pt-0 last:pb-0 sm:flex-row sm:justify-between">
                    <div className="min-w-0">
                      <div className="flex flex-wrap gap-1.5">
                        <Badge>{e.direction}</Badge>
                        {e.attachment_count > 0 ? (
                          <Badge tone="neutral">{e.attachment_count} att.</Badge>
                        ) : null}
                      </div>
                      <p className="mt-1 font-medium">
                        {e.link ? (
                          <a href={e.link} target="_blank" rel="noreferrer" className="hover:underline">
                            {e.subject || "(no subject)"}
                          </a>
                        ) : (
                          e.subject || "(no subject)"
                        )}
                      </p>
                      <p className="text-xs text-muted-foreground">{e.sender}</p>
                      <p className="mt-1 line-clamp-2 text-sm text-muted-foreground">{e.snippet}</p>
                    </div>
                    <p className="shrink-0 text-xs text-muted-foreground">
                      {e.received_at ? new Date(e.received_at).toLocaleString() : "—"}
                    </p>
                  </li>
                ))}
              </ul>
            )}
          </Panel>
          <Panel title="Attach unassigned email to this matter">
            {(o?.unassigned_emails.length ?? 0) === 0 ? (
              <p className="text-sm text-muted-foreground">
                No unassigned emails.{" "}
                <Link href="/integrations" className="underline">
                  Sync Gmail
                </Link>
              </p>
            ) : (
              <ul className="space-y-2">
                {o!.unassigned_emails.map((e) => (
                  <li
                    key={e.id}
                    className="flex flex-wrap items-center justify-between gap-2 rounded-md border px-3 py-2"
                  >
                    <div className="min-w-0">
                      <p className="truncate text-sm font-medium">{e.subject || "(no subject)"}</p>
                      <p className="text-xs text-muted-foreground">{e.sender}</p>
                    </div>
                    <Button
                      size="sm"
                      loading={attachEmail.isPending}
                      onClick={() => attachEmail.mutate(e.id)}
                    >
                      {attachEmail.isPending ? "Attaching…" : "Attach here"}
                    </Button>
                  </li>
                ))}
              </ul>
            )}
          </Panel>
        </div>
      ) : null}

      {tab === "documents" ? (
        <div className="space-y-4">
          <Panel title={`Linked documents (${o?.documents.length ?? 0})`}>
            {(o?.documents.length ?? 0) === 0 ? (
              <p className="text-sm text-muted-foreground">
                No documents on this matter yet. Attach below or sync Drive/Dropbox.
              </p>
            ) : (
              <ul className="divide-y divide-border/70">
                {o!.documents.map((d) => (
                  <li key={d.id} className="flex flex-wrap items-center justify-between gap-2 py-3 first:pt-0">
                    <div>
                      <div className="flex flex-wrap gap-1.5">
                        <Badge>{d.source_system}</Badge>
                        {d.has_text ? <Badge tone="success">Text extracted</Badge> : null}
                      </div>
                      <p className="mt-1 font-medium">
                        {d.link ? (
                          <a href={d.link} target="_blank" rel="noreferrer" className="hover:underline">
                            {d.file_name}
                          </a>
                        ) : (
                          d.file_name
                        )}
                      </p>
                      <p className="text-xs text-muted-foreground">{d.path}</p>
                    </div>
                    <div className="flex flex-col items-end gap-2">
                      <p className="text-xs text-muted-foreground">
                        {d.modified_at ? new Date(d.modified_at).toLocaleString() : "—"}
                      </p>
                      {!d.has_text ? (
                        <Button
                          size="sm"
                          variant="outline"
                          loading={extractDoc.isPending}
                          onClick={() => extractDoc.mutate(d.id)}
                        >
                          {extractDoc.isPending ? "Extracting…" : "Extract text"}
                        </Button>
                      ) : null}
                    </div>
                  </li>
                ))}
              </ul>
            )}
          </Panel>
          <Panel title="Attach unassigned document to this matter">
            {(o?.unassigned_documents.length ?? 0) === 0 ? (
              <p className="text-sm text-muted-foreground">
                No unassigned documents.{" "}
                <Link href="/integrations" className="underline">
                  Sync sources
                </Link>
              </p>
            ) : (
              <ul className="space-y-2">
                {o!.unassigned_documents.map((d) => (
                  <li
                    key={d.id}
                    className="flex flex-wrap items-center justify-between gap-2 rounded-md border px-3 py-2"
                  >
                    <div>
                      <p className="text-sm font-medium">{d.file_name}</p>
                      <p className="text-xs text-muted-foreground">{d.source_system}</p>
                    </div>
                    <Button
                      size="sm"
                      loading={attachDoc.isPending}
                      onClick={() => attachDoc.mutate(d.id)}
                    >
                      {attachDoc.isPending ? "Attaching…" : "Attach here"}
                    </Button>
                  </li>
                ))}
              </ul>
            )}
          </Panel>
        </div>
      ) : null}

      {tab === "billing" ? (
        <div className="space-y-4">
          <Panel title="Propose time / billing entry">
            <form
              className="grid gap-3 md:grid-cols-2"
              onSubmit={(e) => {
                e.preventDefault();
                createBilling.mutate();
              }}
            >
              <div>
                <Label>Date</Label>
                <Input
                  type="date"
                  required
                  value={billingForm.activity_date}
                  onChange={(e) => setBillingForm({ ...billingForm, activity_date: e.target.value })}
                />
              </div>
              <div>
                <Label>Hours</Label>
                <Input
                  type="number"
                  step="0.1"
                  value={billingForm.time_charge}
                  onChange={(e) => setBillingForm({ ...billingForm, time_charge: e.target.value })}
                />
              </div>
              <div className="md:col-span-2">
                <Label>Description</Label>
                <Input
                  required
                  value={billingForm.description}
                  onChange={(e) => setBillingForm({ ...billingForm, description: e.target.value })}
                />
              </div>
              <div>
                <Label>Code (optional)</Label>
                <select
                  className="mt-1 w-full rounded-md border bg-background px-3 py-2 text-sm"
                  value={billingForm.code}
                  onChange={(e) => setBillingForm({ ...billingForm, code: e.target.value })}
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
                <Button type="submit" loading={createBilling.isPending}>
                  {createBilling.isPending ? "Saving…" : "Propose entry"}
                </Button>
              </div>
              {createBilling.error ? (
                <p className="text-sm text-destructive md:col-span-2">
                  {(createBilling.error as Error).message}
                </p>
              ) : null}
            </form>
          </Panel>
          <Panel title={`Billing entries (${o?.billing.length ?? 0})`}>
            {(o?.billing.length ?? 0) === 0 ? (
              <p className="text-sm text-muted-foreground">No billing lines yet — propose one above.</p>
            ) : (
              <div className="overflow-x-auto">
                <table className="w-full text-left text-sm">
                  <thead className="border-b text-xs uppercase text-muted-foreground">
                    <tr>
                      <th className="py-2 pr-3">Date</th>
                      <th className="py-2 pr-3">Description</th>
                      <th className="py-2 pr-3">Code</th>
                      <th className="py-2 pr-3">Hours</th>
                      <th className="py-2 pr-3">Amount</th>
                      <th className="py-2 pr-3">Status</th>
                      <th className="py-2" />
                    </tr>
                  </thead>
                  <tbody>
                    {o!.billing.map((b) => (
                      <tr key={b.id} className="border-b last:border-0">
                        <td className="py-2.5 pr-3">{b.activity_date}</td>
                        <td className="py-2.5 pr-3">{b.description}</td>
                        <td className="py-2.5 pr-3">{b.code || "—"}</td>
                        <td className="py-2.5 pr-3">{b.time_charge ?? "—"}</td>
                        <td className="py-2.5 pr-3">
                          {b.total_amount != null ? `$${b.total_amount.toFixed(2)}` : "—"}
                        </td>
                        <td className="py-2.5 pr-3">
                          <Badge tone={b.approval_status === "pending" ? "warning" : "success"}>
                            {b.approval_status}
                          </Badge>
                        </td>
                        <td className="py-2.5">
                          {b.approval_status === "pending" ? (
                            <div className="flex gap-2">
                              <button
                                className="text-xs underline disabled:opacity-50"
                                disabled={decideBilling.isPending}
                                onClick={() => decideBilling.mutate({ id: b.id, approve: true })}
                              >
                                {decideBilling.isPending ? "…" : "Approve"}
                              </button>
                              <button
                                className="text-xs underline disabled:opacity-50"
                                disabled={decideBilling.isPending}
                                onClick={() => decideBilling.mutate({ id: b.id, approve: false })}
                              >
                                Reject
                              </button>
                            </div>
                          ) : null}
                        </td>
                      </tr>
                    ))}
                  </tbody>
                </table>
              </div>
            )}
          </Panel>
        </div>
      ) : null}

      {tab === "expenses" ? (
        <div className="grid gap-4 lg:grid-cols-2">
          <Panel title="Add expense">
            <form
              className="space-y-3"
              onSubmit={(e) => {
                e.preventDefault();
                createExpense.mutate();
              }}
            >
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
              <div>
                <Label>Notes</Label>
                <Input
                  value={expenseForm.notes}
                  onChange={(e) => setExpenseForm({ ...expenseForm, notes: e.target.value })}
                />
              </div>
              <Button type="submit" loading={createExpense.isPending}>
                {createExpense.isPending ? "Saving…" : "Save expense"}
              </Button>
            </form>
            <ul className="mt-5 space-y-2 border-t pt-4">
              {(o?.expenses ?? []).map((e) => (
                <li key={e.id} className="flex items-center justify-between gap-2 text-sm">
                  <div>
                    <p className="font-medium">
                      ${e.amount.toFixed(2)} · {e.vendor || e.category}
                    </p>
                    <Badge tone={e.approval_status === "pending" ? "warning" : "success"}>
                      {e.approval_status}
                    </Badge>
                  </div>
                  {e.approval_status === "pending" ? (
                    <div className="flex gap-2 text-xs">
                      <button
                        className="underline disabled:opacity-50"
                        disabled={decideExpense.isPending}
                        onClick={() => decideExpense.mutate({ id: e.id, approve: true })}
                      >
                        Approve
                      </button>
                      <button
                        className="underline disabled:opacity-50"
                        disabled={decideExpense.isPending}
                        onClick={() => decideExpense.mutate({ id: e.id, approve: false })}
                      >
                        Reject
                      </button>
                    </div>
                  ) : null}
                </li>
              ))}
            </ul>
          </Panel>
          <Panel title="Add mileage">
            <form
              className="space-y-3"
              onSubmit={(e) => {
                e.preventDefault();
                createMileage.mutate();
              }}
            >
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
              <div className="grid grid-cols-2 gap-2">
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
              </div>
              <Button type="submit" loading={createMileage.isPending}>
                {createMileage.isPending ? "Saving…" : "Save mileage"}
              </Button>
            </form>
            <ul className="mt-5 space-y-2 border-t pt-4">
              {(o?.mileage ?? []).map((row) => (
                <li key={row.id} className="flex items-center justify-between gap-2 text-sm">
                  <div>
                    <p className="font-medium">
                      {row.miles} mi · ${row.mileage_amount.toFixed(2)}
                    </p>
                    <p className="text-xs text-muted-foreground">
                      {row.origin || "?"} → {row.destination || "?"}
                    </p>
                  </div>
                  {row.approval_status === "pending" ? (
                    <div className="flex gap-2 text-xs">
                      <button
                        className="underline disabled:opacity-50"
                        disabled={decideMileage.isPending}
                        onClick={() => decideMileage.mutate({ id: row.id, approve: true })}
                      >
                        Approve
                      </button>
                      <button
                        className="underline disabled:opacity-50"
                        disabled={decideMileage.isPending}
                        onClick={() => decideMileage.mutate({ id: row.id, approve: false })}
                      >
                        Reject
                      </button>
                    </div>
                  ) : (
                    <Badge tone="success">{row.approval_status}</Badge>
                  )}
                </li>
              ))}
            </ul>
          </Panel>
        </div>
      ) : null}

      {tab === "entities" ? (
        <div className="space-y-4">
          <Panel title="Link entity to this matter">
            <form
              className="flex flex-wrap items-end gap-3"
              onSubmit={(e) => {
                e.preventDefault();
                linkEntity.mutate();
              }}
            >
              <div className="min-w-[220px] flex-1">
                <Label>Entity</Label>
                <select
                  className="mt-1 w-full rounded-md border bg-background px-3 py-2 text-sm"
                  required
                  value={entityLink.entity_id}
                  onChange={(e) => setEntityLink({ ...entityLink, entity_id: e.target.value })}
                >
                  <option value="">Select…</option>
                  {(entitiesOpts.data?.items ?? []).map((ent) => (
                    <option key={ent.id} value={ent.id}>
                      {ent.display_name}
                    </option>
                  ))}
                </select>
              </div>
              <div>
                <Label>Role</Label>
                <select
                  className="mt-1 w-full rounded-md border bg-background px-3 py-2 text-sm"
                  value={entityLink.role}
                  onChange={(e) => setEntityLink({ ...entityLink, role: e.target.value })}
                >
                  {["insured", "carrier", "counsel", "vendor", "adjuster", "witness", "other"].map(
                    (r) => (
                      <option key={r} value={r}>
                        {r}
                      </option>
                    ),
                  )}
                </select>
              </div>
              <Button
                type="submit"
                loading={linkEntity.isPending}
                disabled={!entityLink.entity_id}
              >
                {linkEntity.isPending ? "Linking…" : "Link"}
              </Button>
            </form>
            {linkEntity.error ? (
              <p className="mt-2 text-sm text-destructive">{(linkEntity.error as Error).message}</p>
            ) : null}
          </Panel>
          <Panel title={`Related entities (${o?.entities.length ?? 0})`}>
            {(o?.entities.length ?? 0) === 0 ? (
              <p className="text-sm text-muted-foreground">
                No entities linked yet. Create one under Entities, then link here.
              </p>
            ) : (
              <ul className="space-y-2">
                {o!.entities.map((ent) => (
                  <li
                    key={`${ent.relationship_id || ent.id}-${ent.role}`}
                    className="flex items-center justify-between gap-2 rounded-md border px-3 py-2"
                  >
                    <Link href={`/entities/${ent.id}`} className="min-w-0 flex-1 hover:underline">
                      <span className="font-medium">{ent.display_name}</span>
                      <Badge className="ml-2">{ent.role}</Badge>
                    </Link>
                    {ent.relationship_id ? (
                      <Button
                        size="sm"
                        variant="outline"
                        loading={unlinkEntity.isPending}
                        onClick={() => unlinkEntity.mutate(ent.relationship_id!)}
                      >
                        Unlink
                      </Button>
                    ) : null}
                  </li>
                ))}
              </ul>
            )}
          </Panel>
        </div>
      ) : null}

      {tab === "discrepancies" ? (
        <Panel title={`Open discrepancies (${o?.discrepancies?.length ?? 0})`}>
          {(o?.discrepancies?.length ?? 0) === 0 ? (
            <p className="text-sm text-muted-foreground">
              No open field conflicts. When imported claim/policy values differ from the approved matter
              record, they appear here.
            </p>
          ) : (
            <ul className="space-y-3">
              {o!.discrepancies!.map((d) => (
                <li key={d.id} className="rounded-md border p-3">
                  <div className="flex flex-wrap items-center justify-between gap-2">
                    <Badge tone="warning">{d.field_name}</Badge>
                    <Button
                      size="sm"
                      variant="outline"
                      loading={resolveDiscrepancy.isPending}
                      onClick={() => resolveDiscrepancy.mutate(d.id)}
                    >
                      {resolveDiscrepancy.isPending ? "Resolving…" : "Resolve"}
                    </Button>
                  </div>
                  <p className="mt-2 text-sm">
                    Approved: <span className="font-medium">{d.approved_value || "—"}</span>
                  </p>
                  <p className="text-sm">
                    Imported: <span className="font-medium">{d.imported_value || "—"}</span>
                  </p>
                  {d.source ? (
                    <p className="mt-1 text-xs text-muted-foreground">Source: {d.source}</p>
                  ) : null}
                </li>
              ))}
            </ul>
          )}
        </Panel>
      ) : null}

      {tab === "review" ? (
        <Panel title={`Open review items (${o?.review_items.length ?? 0})`}>
          {(o?.review_items.length ?? 0) === 0 ? (
            <p className="text-sm text-muted-foreground">No open review items for this matter.</p>
          ) : (
            <ul className="space-y-3">
              {o!.review_items.map((r) => (
                <li key={r.id} className="rounded-md border p-3">
                  <div className="flex flex-wrap items-center gap-2">
                    <Badge
                      tone={
                        r.priority === "high" ? "danger" : r.priority === "medium" ? "warning" : "neutral"
                      }
                    >
                      {r.priority}
                    </Badge>
                    <Badge>{r.item_type}</Badge>
                  </div>
                  <p className="mt-2 text-sm font-medium">{r.title}</p>
                  {r.explanation ? (
                    <p className="mt-1 text-xs text-muted-foreground">{r.explanation}</p>
                  ) : null}
                </li>
              ))}
            </ul>
          )}
          <div className="mt-4">
            <Button asChild variant="outline" size="sm">
              <Link href="/review-queue">Open full review board</Link>
            </Button>
          </div>
        </Panel>
      ) : null}

      {(exportTe.error || generateSummary.error || createExpense.error || createMileage.error) && (
        <p className="text-sm text-destructive">
          {(exportTe.error as Error)?.message ||
            (generateSummary.error as Error)?.message ||
            (createExpense.error as Error)?.message ||
            (createMileage.error as Error)?.message}
        </p>
      )}
    </div>
  );
}

function Row({ label, value }: { label: string; value?: string | number }) {
  return (
    <div className="flex justify-between gap-4 border-b border-border/50 pb-2 last:border-0 last:pb-0">
      <dt className="text-muted-foreground">{label}</dt>
      <dd className="max-w-[60%] text-right font-medium">{value ?? "—"}</dd>
    </div>
  );
}

function Glance({
  label,
  value,
  onClick,
}: {
  label: string;
  value?: number;
  onClick: () => void;
}) {
  return (
    <button
      onClick={onClick}
      className="rounded-md border bg-muted/30 px-4 py-3 text-left transition hover:bg-muted/60"
    >
      <p className="text-xs uppercase tracking-wide text-muted-foreground">{label}</p>
      <p className="mt-1 font-display text-2xl font-semibold">{value ?? 0}</p>
    </button>
  );
}
