"use client";

import * as React from "react";
import * as ToastPrimitives from "@radix-ui/react-toast";
import { X } from "lucide-react";
import { cn } from "@/lib/utils";

type ToastMessage = {
  id: string;
  title?: string;
  description?: string;
  variant?: "default" | "destructive";
};

const ToastContext = React.createContext<{
  toast: (msg: Omit<ToastMessage, "id">) => void;
} | null>(null);

export function useToast() {
  const ctx = React.useContext(ToastContext);
  if (!ctx) throw new Error("useToast must be used within ToastProvider");
  return ctx;
}

export function ToastProvider({ children }: { children: React.ReactNode }) {
  const [items, setItems] = React.useState<ToastMessage[]>([]);
  const toast = React.useCallback((msg: Omit<ToastMessage, "id">) => {
    const id = crypto.randomUUID();
    setItems((prev) => [...prev, { ...msg, id }]);
  }, []);

  return (
    <ToastContext.Provider value={{ toast }}>
      <ToastPrimitives.Provider>
        {children}
        {items.map((item) => (
          <ToastPrimitives.Root
            key={item.id}
            className={cn(
              "group pointer-events-auto relative flex w-full items-center justify-between space-x-4 overflow-hidden rounded-md border p-4 pr-8 shadow-lg transition-all data-[state=open]:animate-in data-[state=closed]:animate-out",
              item.variant === "destructive"
                ? "border-destructive bg-destructive text-destructive-foreground"
                : "border bg-card text-card-foreground",
            )}
            duration={4000}
            onOpenChange={(open) => {
              if (!open) {
                setItems((prev) => prev.filter((t) => t.id !== item.id));
              }
            }}
          >
            <div className="grid gap-1">
              {item.title ? (
                <ToastPrimitives.Title className="text-sm font-semibold">
                  {item.title}
                </ToastPrimitives.Title>
              ) : null}
              {item.description ? (
                <ToastPrimitives.Description className="text-sm opacity-90">
                  {item.description}
                </ToastPrimitives.Description>
              ) : null}
            </div>
            <ToastPrimitives.Close className="absolute right-2 top-2 rounded-md p-1 opacity-70">
              <X className="h-4 w-4" />
            </ToastPrimitives.Close>
          </ToastPrimitives.Root>
        ))}
        <ToastPrimitives.Viewport
          className="fixed top-0 z-[100] flex max-h-screen w-full flex-col-reverse p-4 sm:bottom-0 sm:right-0 sm:top-auto sm:flex-col md:max-w-[420px]"
          suppressHydrationWarning
        />
      </ToastPrimitives.Provider>
    </ToastContext.Provider>
  );
}

/** @deprecated Use ToastProvider wrapping the app */
export function Toaster() {
  return null;
}
