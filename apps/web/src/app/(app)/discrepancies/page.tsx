"use client";

import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import Link from "next/link";
import { useState } from "react";
import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import { EmptyState, PageHeader, Panel } from "@/components/ui/page";
import { apiGet, apiSend } from "@/lib/api-client";

type Alert = {
  id: string;
  matter_id: string;
  matter_name?: string;
  matter_number?: string;
  field_name: string;
  approved_value?: string;
  imported_value?: string;
  source?: string;
  status: string;
  notes?: string;
  created_at?: string;
};

export default function DiscrepanciesPage() {
  const qc = useQueryClient();
  const [status, setStatus] = useState<"open" | "resolved" | "all">("open");

  const { data = [], isLoading, error } = useQuery({
    queryKey: ["discrepancies", status],
    queryFn: () =>
      apiGet<Alert[]>(
        `/api/v1/discrepancies?status=${status}`,
      ),
  });

  const resolve = useMutation({
    mutationFn: (id: string) => apiSend(`/api/v1/discrepancies/${id}/resolve`, "POST"),
    onSuccess: () => {
      qc.invalidateQueries({ queryKey: ["discrepancies"] });
      qc.invalidateQueries({ queryKey: ["matter-overview"] });
    },
  });

  return (
    <div className="space-y-6">
      <PageHeader
        eyebrow="Integrity"
        title="Discrepancy alerts"
        description="Imported claim/policy/case values that conflict with the approved matter record. Resolve after you confirm the correct value."
      />

      <div className="flex flex-wrap gap-2">
        {(
          [
            ["open", "Open"],
            ["resolved", "Resolved"],
            ["all", "All"],
          ] as const
        ).map(([id, label]) => (
          <button
            key={id}
            onClick={() => setStatus(id)}
            className={`rounded-full border px-3 py-1.5 text-xs font-medium ${
              status === id
                ? "border-primary bg-primary text-primary-foreground"
                : "border-border bg-card/80 text-muted-foreground"
            }`}
          >
            {label}
          </button>
        ))}
      </div>

      {error ? <p className="text-sm text-destructive">{(error as Error).message}</p> : null}

      <Panel title={`${data.length} alerts`}>
        {isLoading ? (
          <p className="text-sm text-muted-foreground">Loading…</p>
        ) : data.length === 0 ? (
          <EmptyState
            title="No discrepancy alerts"
            description="Conflicts appear when Gmail association finds claim/policy/case numbers that differ from the matter file."
          />
        ) : (
          <ul className="divide-y divide-border/70">
            {data.map((d) => (
              <li
                key={d.id}
                className="flex flex-col gap-3 py-4 first:pt-0 last:pb-0 sm:flex-row sm:items-start sm:justify-between"
              >
                <div className="min-w-0 space-y-1.5">
                  <div className="flex flex-wrap gap-1.5">
                    <Badge tone={d.status === "open" ? "warning" : "success"}>{d.status}</Badge>
                    <Badge>{d.field_name.replaceAll("_", " ")}</Badge>
                    {d.source ? <Badge tone="neutral">{d.source}</Badge> : null}
                  </div>
                  <p className="font-medium">
                    <Link href={`/matters/${d.matter_id}`} className="hover:underline">
                      {d.matter_number ? `${d.matter_number} · ` : ""}
                      {d.matter_name || "Matter"}
                    </Link>
                  </p>
                  <p className="text-sm text-muted-foreground">
                    Approved: <span className="text-foreground">{d.approved_value || "—"}</span>
                    {" · "}
                    Imported: <span className="text-foreground">{d.imported_value || "—"}</span>
                  </p>
                  {d.notes ? <p className="text-xs text-muted-foreground">{d.notes}</p> : null}
                  {d.created_at ? (
                    <p className="text-xs text-muted-foreground">
                      {new Date(d.created_at).toLocaleString()}
                    </p>
                  ) : null}
                </div>
                {d.status === "open" ? (
                  <Button
                    size="sm"
                    disabled={resolve.isPending}
                    onClick={() => resolve.mutate(d.id)}
                  >
                    Resolve
                  </Button>
                ) : null}
              </li>
            ))}
          </ul>
        )}
      </Panel>
    </div>
  );
}
