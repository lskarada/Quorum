// Minimal ScrollArea shell — plain overflow container.
// Replace with `shadcn add scroll-area` for Radix-backed custom scrollbars.
import { forwardRef, type HTMLAttributes } from "react";
import { cn } from "@/lib/utils";

export const ScrollArea = forwardRef<HTMLDivElement, HTMLAttributes<HTMLDivElement>>(
  ({ className, children, ...props }, ref) => (
    <div ref={ref} className={cn("overflow-auto", className)} {...props}>
      {children}
    </div>
  ),
);
ScrollArea.displayName = "ScrollArea";
