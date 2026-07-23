"use client";

import Link from "next/link";
import { useQuery } from "@tanstack/react-query";
import { useState } from "react";
import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { EmptyState, PageHeader } from "@/components/ui/page";
import { apiGet } from "@/lib/api-client";

type Matter = {
  id: string;
  matter_number: string;
  name: string;
  claim_number?: string;
  property_address?: string;
  is_personal: boolean;
  status: { name: string; code: string };
  billing_classification: { name: string; code: string };
  matter_type: { name: string };
};

export default function MattersPage() {
  const [search, setSearch] = useState("");
  const { data, isLoading, error } = useQuery({
    queryKey: ["matters", search],
    queryFn: () =>
      apiGet<{ items: Matter[]; total: number }>(
        `/api/v1/matters?page_size=50${search ? `&search=${encodeURIComponent(search)}` : ""}`,
      ),
  });

  return (
    <div className="space-y-6">
      <PageHeader
        eyebrow="Matter files"
        title="Matters"
        description="Every email, document, expense, and billing line hangs off a matter. Open a file to work the case."
        actions={
          <Button asChild>
            <Link href="/matters/new">Create matter</Link>
          </Button>
        }
      />

      <div className="flex flex-wrap items-center gap-3">
        <Input
          placeholder="Search name, claim, policy, address…"
          value={search}
          onChange={(e) => setSearch(e.target.value)}
          className="max-w-md bg-card/80"
        />
        <p className="text-xs text-muted-foreground">{data?.total ?? 0} matters</p>
      </div>

      {error ? <p className="text-sm text-destructive">{(error as Error).message}</p> : null}

      {isLoading ? (
        <div className="umic-panel p-10 text-center text-sm text-muted-foreground">Loading matters…</div>
      ) : data?.items.length ? (
        <div className="grid gap-3 md:grid-cols-2 xl:grid-cols-3">
          {data.items.map((m) => (
            <Link
              key={m.id}
              href={`/matters/${m.id}`}
              className="umic-panel group block p-5 transition hover:-translate-y-0.5 hover:shadow-lift"
            >
              <div className="flex items-start justify-between gap-2">
                <p className="text-[11px] font-semibold uppercase tracking-wider text-muted-foreground">
                  {m.matter_number}
                </p>
                <Badge>{m.status.name}</Badge>
              </div>
              <h3 className="mt-2 font-display text-lg font-semibold leading-snug tracking-tight group-hover:text-primary">
                {m.name}
              </h3>
              <p className="mt-2 line-clamp-1 text-sm text-muted-foreground">
                {m.property_address || m.matter_type.name}
              </p>
              <div className="mt-4 flex flex-wrap gap-1.5">
                <Badge tone="neutral">{m.matter_type.name}</Badge>
                <Badge
                  tone={m.billing_classification.code === "billable" ? "success" : "warning"}
                >
                  {m.billing_classification.name}
                </Badge>
                {m.claim_number ? <Badge tone="neutral">Claim {m.claim_number}</Badge> : null}
                {m.is_personal ? <Badge tone="danger">Personal</Badge> : null}
              </div>
            </Link>
          ))}
        </div>
      ) : (
        <EmptyState
          title="No matters yet"
          description="Create the first matter file, then sync Gmail/Drive and associate records to it."
          action={
            <Button asChild>
              <Link href="/matters/new">Create matter</Link>
            </Button>
          }
        />
      )}
    </div>
  );
}
