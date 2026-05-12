// Stub Dialog shell. Use `shadcn add dialog` to install the real Radix-backed
// dialog. This stub exists so imports resolve during scaffolding; no modal behavior.
import type { ReactNode } from "react";

interface DialogProps {
  open?: boolean;
  onOpenChange?: (open: boolean) => void;
  children?: ReactNode;
}

export function Dialog({ children }: DialogProps) {
  return <>{children}</>;
}
export function DialogTrigger({ children }: { children?: ReactNode }) {
  return <>{children}</>;
}
export function DialogContent({ children }: { children?: ReactNode }) {
  return <div>{children}</div>;
}
export function DialogHeader({ children }: { children?: ReactNode }) {
  return <div>{children}</div>;
}
export function DialogTitle({ children }: { children?: ReactNode }) {
  return <h2>{children}</h2>;
}
export function DialogDescription({ children }: { children?: ReactNode }) {
  return <p>{children}</p>;
}
