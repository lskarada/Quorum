interface TopBarProps {
  panelLabel?: string;
  status?: string;
  running?: boolean;
}

/**
 * Full-width app bar: brand mark + optional panel chip + live status.
 * A pulsing green dot shows while `running`.
 */
export function TopBar({ panelLabel, status, running }: TopBarProps) {
  return (
    <div className="flex items-center gap-3.5 rounded-xl border border-line bg-card px-[18px] py-3 shadow-card-1">
      <div className="flex items-center gap-2 text-[17px] font-extrabold tracking-tight">
        <span
          className="h-[22px] w-[22px] rounded-md"
          style={{ background: "linear-gradient(135deg, hsl(217 91% 60%), hsl(280 91% 60%))" }}
        />
        Quorum
      </div>
      {panelLabel && (
        <span className="ml-1 flex items-center gap-1.5 rounded-full border border-line bg-surface-2 px-2.5 py-1 text-[12.5px] text-muted-foreground">
          Panel: <b className="font-semibold text-ink-2">{panelLabel}</b>
        </span>
      )}
      {status && (
        <span className="ml-auto flex items-center gap-2 text-[12.5px] font-semibold text-ink-2">
          {running && <span className="h-2 w-2 rounded-full bg-ok animate-livepulse" />}
          {status}
        </span>
      )}
    </div>
  );
}
