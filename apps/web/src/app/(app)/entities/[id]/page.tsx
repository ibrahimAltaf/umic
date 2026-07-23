"use client";

import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import Link from "next/link";
import { useParams } from "next/navigation";
import { useEffect, useState } from "react";
import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import { PageHeader, Panel } from "@/components/ui/page";
import { apiGet, apiSend } from "@/lib/api-client";

type Entity = {
  id: string;
  display_name: string;
  legal_name: string;
  primary_email?: string;
  primary_phone?: string;
  primary_domain?: string;
  notes?: string;
  status: string;
  entity_type: { name: string };
  aliases: string[];
};

export default function EntityDetailPage() {
  const params = useParams<{ id: string }>();
  const qc = useQueryClient();
  const [editing, setEditing] = useState(false);
  const [form, setForm] = useState({
    display_name: "",
    legal_name: "",
    primary_email: "",
    primary_phone: "",
    primary_domain: "",
    notes: "",
    status: "active",
  });

  const { data: e, isLoading, error } = useQuery({
    queryKey: ["entity", params.id],
    queryFn: () => apiGet<Entity>(`/api/v1/entities/${params.id}`),
  });

  useEffect(() => {
    if (!e) return;
    setForm({
      display_name: e.display_name || "",
      legal_name: e.legal_name || "",
      primary_email: e.primary_email || "",
      primary_phone: e.primary_phone || "",
      primary_domain: e.primary_domain || "",
      notes: e.notes || "",
      status: e.status || "active",
    });
  }, [e]);

  const save = useMutation({
    mutationFn: () =>
      apiSend(`/api/v1/entities/${params.id}`, "PATCH", {
        display_name: form.display_name || null,
        legal_name: form.legal_name || null,
        primary_email: form.primary_email || null,
        primary_phone: form.primary_phone || null,
        primary_domain: form.primary_domain || null,
        notes: form.notes || null,
        status: form.status,
      }),
    onSuccess: () => {
      setEditing(false);
      qc.invalidateQueries({ queryKey: ["entity", params.id] });
      qc.invalidateQueries({ queryKey: ["entities"] });
    },
  });

  if (isLoading) {
    return <div className="umic-panel p-10 text-center text-sm text-muted-foreground">Loading…</div>;
  }
  if (error) return <p className="text-destructive">{(error as Error).message}</p>;
  if (!e) return null;

  return (
    <div className="space-y-6">
      <PageHeader
        eyebrow="Entity record"
        title={e.display_name}
        description={e.legal_name}
        actions={
          <>
            <Button asChild variant="outline">
              <Link href="/entities">Back to entities</Link>
            </Button>
            <Button variant={editing ? "outline" : "default"} onClick={() => setEditing((v) => !v)}>
              {editing ? "Cancel edit" : "Edit"}
            </Button>
          </>
        }
      />
      <div className="flex flex-wrap gap-2">
        <Badge>{e.entity_type.name}</Badge>
        <Badge tone={e.status === "active" ? "success" : "neutral"}>{e.status}</Badge>
      </div>

      {editing ? (
        <Panel title="Edit entity">
          <form
            className="grid gap-3 md:grid-cols-2"
            onSubmit={(e) => {
              e.preventDefault();
              save.mutate();
            }}
          >
            <div>
              <Label>Display name</Label>
              <Input
                value={form.display_name}
                onChange={(ev) => setForm({ ...form, display_name: ev.target.value })}
              />
            </div>
            <div>
              <Label>Legal name</Label>
              <Input
                value={form.legal_name}
                onChange={(ev) => setForm({ ...form, legal_name: ev.target.value })}
              />
            </div>
            <div>
              <Label>Email</Label>
              <Input
                value={form.primary_email}
                onChange={(ev) => setForm({ ...form, primary_email: ev.target.value })}
              />
            </div>
            <div>
              <Label>Phone</Label>
              <Input
                value={form.primary_phone}
                onChange={(ev) => setForm({ ...form, primary_phone: ev.target.value })}
              />
            </div>
            <div>
              <Label>Domain</Label>
              <Input
                value={form.primary_domain}
                onChange={(ev) => setForm({ ...form, primary_domain: ev.target.value })}
              />
            </div>
            <div>
              <Label>Status</Label>
              <select
                className="mt-1 w-full rounded-md border bg-background px-3 py-2 text-sm"
                value={form.status}
                onChange={(ev) => setForm({ ...form, status: ev.target.value })}
              >
                <option value="active">Active</option>
                <option value="inactive">Inactive</option>
              </select>
            </div>
            <div className="md:col-span-2">
              <Label>Notes</Label>
              <Input
                value={form.notes}
                onChange={(ev) => setForm({ ...form, notes: ev.target.value })}
              />
            </div>
            <div className="md:col-span-2">
              <Button type="submit" disabled={save.isPending}>
                {save.isPending ? "Saving…" : "Save changes"}
              </Button>
              {save.error ? (
                <p className="mt-2 text-sm text-destructive">{(save.error as Error).message}</p>
              ) : null}
            </div>
          </form>
        </Panel>
      ) : (
        <Panel title="Contact & identity">
          <dl className="space-y-2.5 text-sm">
            <Row label="Legal name" value={e.legal_name} />
            <Row label="Email" value={e.primary_email} />
            <Row label="Phone" value={e.primary_phone} />
            <Row label="Domain" value={e.primary_domain} />
            <Row label="Aliases" value={e.aliases.join(", ") || undefined} />
            <Row label="Notes" value={e.notes} />
          </dl>
        </Panel>
      )}
    </div>
  );
}

function Row({ label, value }: { label: string; value?: string }) {
  return (
    <div className="flex justify-between gap-4 border-b border-border/50 pb-2 last:border-0 last:pb-0">
      <dt className="text-muted-foreground">{label}</dt>
      <dd className="max-w-[60%] text-right font-medium">{value ?? "—"}</dd>
    </div>
  );
}
