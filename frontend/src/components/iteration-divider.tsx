interface IterationDividerProps {
  iteration: number;
}

/**
 * Divider between iterations of the multi-iter consensus loop. `iteration`
 * is zero-indexed (matches Differential.iteration); displayed one-indexed.
 */
export function IterationDivider({ iteration }: IterationDividerProps) {
  return (
    <div className="my-4 flex items-center gap-3" role="separator">
      <hr className="flex-1 border-line" />
      <span className="text-[10.5px] font-extrabold uppercase tracking-wide text-faint">
        Iteration {iteration + 1}
      </span>
      <hr className="flex-1 border-line" />
    </div>
  );
}
