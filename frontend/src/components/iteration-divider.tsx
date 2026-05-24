interface IterationDividerProps {
  iteration: number;
}

/**
 * Horizontal divider between iterations of the multi-iter consensus loop.
 * `iteration` is zero-indexed (matches Differential.iteration); we display
 * it one-indexed for the clinician audience.
 */
export function IterationDivider({ iteration }: IterationDividerProps) {
  return (
    <div className="flex items-center gap-3 my-6" role="separator">
      <hr className="flex-1 border-muted" />
      <span className="text-sm font-medium text-muted-foreground">
        Iteration {iteration + 1}
      </span>
      <hr className="flex-1 border-muted" />
    </div>
  );
}
