"use client";

import { useQuery } from "@tanstack/react-query";
import { Badge } from "@/components/ui/badge";
import { PageHeader, Panel } from "@/components/ui/page";
import { apiGet } from "@/lib/api-client";

type Event = {
  id: string;
  timestamp: string;
  action: string;
  record_type?: string;
  matter_id?: string;
  source?: string;
};

export default function AuditPage() {
  const { data, isLoading, error } = useQuery({
    queryKey: ["audit"],
    queryFn: () => apiGet<{ items: Event[]; total?: number }>("/api/v1/audit-events?page_size=80"),
  });

  return (
    <div className="space-y-6">
      <PageHeader
        eyebrow="Compliance"
        title="Audit history"
        description="Append-only ledger of material system and user actions — syncs, approvals, associations."
      />
      {error ? <p className="text-sm text-destructive">{(error as Error).message}</p> : null}
      <Panel title={`${data?.items?.length ?? 0} recent events`}>
        <div className="overflow-x-auto">
          <table className="w-full text-left text-sm">
            <thead className="border-b text-xs uppercase text-muted-foreground">
              <tr>
                <th className="py-2 pr-3">When</th>
                <th className="py-2 pr-3">Action</th>
                <th className="py-2 pr-3">Record</th>
                <th className="py-2">Source</th>
              </tr>
            </thead>
            <tbody>
              {isLoading ? (
                <tr>
                  <td colSpan={4} className="py-10 text-center text-muted-foreground">
                    Loading…
                  </td>
                </tr>
              ) : (
                (data?.items ?? []).map((e) => (
                  <tr key={e.id} className="border-b last:border-0">
                    <td className="py-3 pr-3 whitespace-nowrap text-muted-foreground">
                      {new Date(e.timestamp).toLocaleString()}
                    </td>
                    <td className="py-3 pr-3 font-medium">{e.action}</td>
                    <td className="py-3 pr-3">
                      <Badge tone="neutral">{e.record_type ?? "—"}</Badge>
                    </td>
                    <td className="py-3 text-muted-foreground">{e.source ?? "—"}</td>
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
