"use client";

import { useQuery } from "@tanstack/react-query";
import { Badge } from "@/components/ui/badge";
import { PageHeader } from "@/components/ui/page";
import { apiGet } from "@/lib/api-client";

type Role = {
  id: string;
  code: string;
  name: string;
  description?: string;
  permissions: { code: string }[];
};

export default function RolesPage() {
  const { data = [], isLoading, error } = useQuery({
    queryKey: ["roles"],
    queryFn: () => apiGet<Role[]>("/api/v1/roles"),
  });

  return (
    <div className="space-y-6">
      <PageHeader
        eyebrow="Administration"
        title="Roles & permissions"
        description="Backend-enforced RBAC. System Owner has the full permission set."
      />
      {error ? <p className="text-sm text-destructive">{(error as Error).message}</p> : null}
      {isLoading ? (
        <div className="umic-panel p-10 text-center text-sm text-muted-foreground">Loading…</div>
      ) : (
        <div className="grid gap-4 md:grid-cols-2">
          {data.map((role) => (
            <div key={role.id} className="umic-panel p-5">
              <div className="flex items-center justify-between gap-2">
                <h3 className="font-display text-lg font-semibold">{role.name}</h3>
                <Badge>{role.permissions.length} perms</Badge>
              </div>
              <p className="mt-1 text-xs uppercase tracking-wide text-muted-foreground">
                {role.code}
              </p>
              <p className="mt-3 text-sm text-muted-foreground">{role.description}</p>
              <div className="mt-4 flex flex-wrap gap-1">
                {role.permissions.slice(0, 10).map((p) => (
                  <Badge key={p.code} tone="neutral">
                    {p.code}
                  </Badge>
                ))}
                {role.permissions.length > 10 ? (
                  <Badge>+{role.permissions.length - 10}</Badge>
                ) : null}
              </div>
            </div>
          ))}
        </div>
      )}
    </div>
  );
}
