import { useState, type ChangeEvent } from "react";
import { Button } from "@/components/ui/button";
import { Card } from "@/components/ui/card";
import { Textarea } from "@/components/ui/textarea";

interface CaseInputProps {
  onStart: (presentation: string) => void;
  disabled?: boolean;
}

/**
 * Left-column case input.
 *
 * TODO: wire a sample-case dropdown (loads a JSON file from data/cases/nejm/),
 * a token-count indicator, and a "clear" affordance.
 */
export function CaseInput({ onStart, disabled }: CaseInputProps) {
  const [presentation, setPresentation] = useState("");

  return (
    <Card className="p-4 space-y-3">
      <h2 className="text-lg font-semibold">Case presentation</h2>
      <Textarea
        value={presentation}
        onChange={(e: ChangeEvent<HTMLTextAreaElement>) => setPresentation(e.target.value)}
        placeholder="Paste a clinical vignette here..."
        rows={12}
        disabled={disabled}
      />
      <Button
        onClick={() => onStart(presentation)}
        disabled={disabled || presentation.trim().length === 0}
        className="w-full"
      >
        {disabled ? "Deliberating..." : "Begin deliberation"}
      </Button>
    </Card>
  );
}
