import { useState, type ChangeEvent } from "react";
import { Button } from "@/components/ui/button";
import { Textarea } from "@/components/ui/textarea";

interface CaseInputProps {
  onStart: (presentation: string) => void;
  disabled?: boolean;
}

/**
 * Left-column case input. Card chrome is provided by the parent route.
 * Placeholder text and button labels are kept verbatim (asserted by tests).
 */
export function CaseInput({ onStart, disabled }: CaseInputProps) {
  const [presentation, setPresentation] = useState("");

  return (
    <div className="space-y-3">
      <h2 className="text-[10.5px] font-extrabold uppercase tracking-wide text-faint">Case presentation</h2>
      <Textarea
        value={presentation}
        onChange={(e: ChangeEvent<HTMLTextAreaElement>) => setPresentation(e.target.value)}
        placeholder="Paste a clinical vignette here..."
        rows={12}
        disabled={disabled}
        className="resize-none rounded-lg border-line bg-surface-2 text-[13px] leading-relaxed text-ink-2"
      />
      <Button
        onClick={() => onStart(presentation)}
        disabled={disabled || presentation.trim().length === 0}
        className="w-full bg-primary font-semibold text-primary-foreground hover:bg-primary/90"
      >
        {disabled ? "Deliberating..." : "Begin deliberation"}
      </Button>
    </div>
  );
}
