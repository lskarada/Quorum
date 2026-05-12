// Stub Sheet shell. Use `shadcn add sheet` to install the real Radix-backed
// drawer. Exists so imports resolve.
import type { ReactNode } from "react";

export function Sheet({ children }: { children?: ReactNode }) {
  return <>{children}</>;
}
export function SheetTrigger({ children }: { children?: ReactNode }) {
  return <>{children}</>;
}
export function SheetContent({ children }: { children?: ReactNode }) {
  return <div>{children}</div>;
}
export function SheetHeader({ children }: { children?: ReactNode }) {
  return <div>{children}</div>;
}
export function SheetTitle({ children }: { children?: ReactNode }) {
  return <h2>{children}</h2>;
}
export function SheetDescription({ children }: { children?: ReactNode }) {
  return <p>{children}</p>;
}
