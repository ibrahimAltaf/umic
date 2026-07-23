"use client";

import { createContext, useContext, useState } from "react";

type Ctx = { open: boolean; setOpen: (v: boolean) => void };

const SidebarCtx = createContext<Ctx>({ open: false, setOpen: () => {} });

export function useMobileNav() {
  return useContext(SidebarCtx);
}

export function MobileNavProvider({ children }: { children: React.ReactNode }) {
  const [open, setOpen] = useState(false);
  return (
    <SidebarCtx.Provider value={{ open, setOpen }}>{children}</SidebarCtx.Provider>
  );
}
