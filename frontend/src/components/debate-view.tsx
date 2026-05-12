import { AgentCard } from "@/components/agent-card";
import { ScrollArea } from "@/components/ui/scroll-area";
import type { AgentMessage } from "@/lib/types";

interface DebateViewProps {
  messages: AgentMessage[];
  running: boolean;
}

/**
 * Center-column live debate feed.
 *
 * TODO (visual pass):
 *   - Per-iteration soft divider when message.iteration changes
 *   - Sticky iteration counter header
 *   - Auto-scroll-to-bottom while running
 *   - Empty state when messages.length === 0 && !running
 */
export function DebateView({ messages, running }: DebateViewProps) {
  if (messages.length === 0 && !running) {
    return (
      <div className="flex h-full items-center justify-center text-muted-foreground">
        Paste a case and hit Begin to start the deliberation.
      </div>
    );
  }

  return (
    <ScrollArea className="h-full">
      <div className="space-y-3">
        {messages.map((msg, idx) => (
          <AgentCard key={`${msg.role}-${msg.iteration}-${idx}`} message={msg} />
        ))}
        {running && (
          <div className="text-sm text-muted-foreground italic">
            Panel is thinking...
          </div>
        )}
      </div>
    </ScrollArea>
  );
}
