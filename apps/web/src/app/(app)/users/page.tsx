"use client";

import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { useState } from "react";
import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import { PageHeader, Panel } from "@/components/ui/page";
import { apiGet, apiSend } from "@/lib/api-client";

type User = {
  id: string;
  email: string;
  first_name: string;
  last_name: string;
  is_active: boolean;
  roles: { name: string; code: string }[];
};

type Role = { code: string; name: string };

export default function UsersPage() {
  const qc = useQueryClient();
  const [showCreate, setShowCreate] = useState(false);
  const [form, setForm] = useState({
    email: "",
    password: "",
    first_name: "",
    last_name: "",
    role_codes: ["viewer"] as string[],
  });

  const { data, isLoading, error } = useQuery({
    queryKey: ["users"],
    queryFn: () => apiGet<{ items: User[] }>("/api/v1/users?page_size=50"),
  });
  const roles = useQuery({
    queryKey: ["roles"],
    queryFn: () => apiGet<Role[]>("/api/v1/roles"),
  });

  const create = useMutation({
    mutationFn: () =>
      apiSend("/api/v1/users", "POST", {
        email: form.email,
        password: form.password,
        first_name: form.first_name,
        last_name: form.last_name,
        role_codes: form.role_codes,
        is_active: true,
      }),
    onSuccess: () => {
      setShowCreate(false);
      setForm({
        email: "",
        password: "",
        first_name: "",
        last_name: "",
        role_codes: ["viewer"],
      });
      qc.invalidateQueries({ queryKey: ["users"] });
    },
  });

  const toggleActive = useMutation({
    mutationFn: ({ id, is_active }: { id: string; is_active: boolean }) =>
      apiSend(`/api/v1/users/${id}`, "PATCH", { is_active }),
    onSuccess: () => qc.invalidateQueries({ queryKey: ["users"] }),
  });

  return (
    <div className="space-y-6">
      <PageHeader
        eyebrow="Administration"
        title="User management"
        description="Administrator-controlled accounts. Roles are enforced in the API, not just the UI."
        actions={
          <Button onClick={() => setShowCreate((v) => !v)}>
            {showCreate ? "Cancel" : "Add user"}
          </Button>
        }
      />
      {error ? <p className="text-sm text-destructive">{(error as Error).message}</p> : null}

      {showCreate ? (
        <Panel title="Create user">
          <form
            className="grid gap-3 md:grid-cols-2"
            onSubmit={(e) => {
              e.preventDefault();
              create.mutate();
            }}
          >
            <div>
              <Label>First name</Label>
              <Input
                required
                value={form.first_name}
                onChange={(e) => setForm({ ...form, first_name: e.target.value })}
              />
            </div>
            <div>
              <Label>Last name</Label>
              <Input
                required
                value={form.last_name}
                onChange={(e) => setForm({ ...form, last_name: e.target.value })}
              />
            </div>
            <div>
              <Label>Email</Label>
              <Input
                type="email"
                required
                value={form.email}
                onChange={(e) => setForm({ ...form, email: e.target.value })}
              />
            </div>
            <div>
              <Label>Password</Label>
              <Input
                type="password"
                required
                minLength={10}
                value={form.password}
                onChange={(e) => setForm({ ...form, password: e.target.value })}
                placeholder="Upper + lower + digit, 10+"
              />
            </div>
            <div className="md:col-span-2">
              <Label>Roles</Label>
              <div className="mt-2 flex flex-wrap gap-2">
                {(roles.data ?? []).map((r) => {
                  const on = form.role_codes.includes(r.code);
                  return (
                    <button
                      key={r.code}
                      type="button"
                      onClick={() =>
                        setForm({
                          ...form,
                          role_codes: on
                            ? form.role_codes.filter((c) => c !== r.code)
                            : [...form.role_codes, r.code],
                        })
                      }
                      className={`rounded-full border px-3 py-1 text-xs font-medium ${
                        on
                          ? "border-primary bg-primary text-primary-foreground"
                          : "border-border text-muted-foreground"
                      }`}
                    >
                      {r.name}
                    </button>
                  );
                })}
              </div>
            </div>
            <div className="md:col-span-2">
              <Button type="submit" disabled={create.isPending || form.role_codes.length === 0}>
                {create.isPending ? "Creating…" : "Create user"}
              </Button>
              {create.error ? (
                <p className="mt-2 text-sm text-destructive">{(create.error as Error).message}</p>
              ) : null}
            </div>
          </form>
        </Panel>
      ) : null}

      <Panel title={`${data?.items.length ?? 0} users`}>
        <div className="overflow-x-auto">
          <table className="w-full text-left text-sm">
            <thead className="border-b text-xs uppercase text-muted-foreground">
              <tr>
                <th className="py-2 pr-3">User</th>
                <th className="py-2 pr-3">Email</th>
                <th className="py-2 pr-3">Roles</th>
                <th className="py-2 pr-3">Status</th>
                <th className="py-2" />
              </tr>
            </thead>
            <tbody>
              {isLoading ? (
                <tr>
                  <td colSpan={5} className="py-10 text-center text-muted-foreground">
                    Loading…
                  </td>
                </tr>
              ) : (
                (data?.items ?? []).map((u) => (
                  <tr key={u.id} className="border-b last:border-0">
                    <td className="py-3 pr-3">
                      <div className="flex items-center gap-3">
                        <span className="flex h-8 w-8 items-center justify-center rounded-full bg-primary/10 text-xs font-semibold text-primary">
                          {u.first_name?.[0]}
                          {u.last_name?.[0]}
                        </span>
                        <span className="font-medium">
                          {u.first_name} {u.last_name}
                        </span>
                      </div>
                    </td>
                    <td className="py-3 pr-3 text-muted-foreground">{u.email}</td>
                    <td className="py-3 pr-3">
                      <div className="flex flex-wrap gap-1">
                        {u.roles.map((r) => (
                          <Badge key={r.code}>{r.name}</Badge>
                        ))}
                      </div>
                    </td>
                    <td className="py-3 pr-3">
                      <Badge tone={u.is_active ? "success" : "danger"}>
                        {u.is_active ? "Active" : "Disabled"}
                      </Badge>
                    </td>
                    <td className="py-3 text-right">
                      <Button
                        size="sm"
                        variant="outline"
                        disabled={toggleActive.isPending}
                        onClick={() =>
                          toggleActive.mutate({ id: u.id, is_active: !u.is_active })
                        }
                      >
                        {u.is_active ? "Disable" : "Enable"}
                      </Button>
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
