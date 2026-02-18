"use client";

import { createContext, useContext, useState, useCallback, type ReactNode } from "react";
import { XCircle, CheckCircle2, AlertTriangle, X } from "lucide-react";
import { cn } from "@/lib/utils";

type ToastLevel = "success" | "error" | "warning";

interface Toast {
  id: number;
  level: ToastLevel;
  message: string;
}

interface ToastContextValue {
  toast: (level: ToastLevel, message: string) => void;
}

const ToastContext = createContext<ToastContextValue>({
  toast: () => {},
});

export const useToast = () => useContext(ToastContext);

let nextId = 0;

export function ToastProvider({ children }: { children: ReactNode }) {
  const [toasts, setToasts] = useState<Toast[]>([]);

  const toast = useCallback((level: ToastLevel, message: string) => {
    const id = ++nextId;
    setToasts((prev) => [...prev, { id, level, message }]);
    setTimeout(() => {
      setToasts((prev) => prev.filter((t) => t.id !== id));
    }, 5000);
  }, []);

  const dismiss = useCallback((id: number) => {
    setToasts((prev) => prev.filter((t) => t.id !== id));
  }, []);

  const Icon = { success: CheckCircle2, error: XCircle, warning: AlertTriangle };
  const colors = {
    success: "border-green-500/30 bg-green-500/10 text-green-700 dark:text-green-400",
    error: "border-red-500/30 bg-red-500/10 text-red-700 dark:text-red-400",
    warning: "border-yellow-500/30 bg-yellow-500/10 text-yellow-700 dark:text-yellow-400",
  };

  return (
    <ToastContext.Provider value={{ toast }}>
      {children}
      <div className="fixed bottom-4 right-4 z-50 flex flex-col gap-2">
        {toasts.map((t) => {
          const I = Icon[t.level];
          return (
            <div
              key={t.id}
              className={cn(
                "flex items-start gap-2 rounded-lg border px-4 py-3 text-sm shadow-lg",
                "animate-in slide-in-from-bottom-2 fade-in duration-200",
                colors[t.level]
              )}
            >
              <I className="mt-0.5 h-4 w-4 shrink-0" />
              <span className="flex-1">{t.message}</span>
              <button onClick={() => dismiss(t.id)} className="shrink-0 opacity-60 hover:opacity-100">
                <X className="h-3.5 w-3.5" />
              </button>
            </div>
          );
        })}
      </div>
    </ToastContext.Provider>
  );
}
