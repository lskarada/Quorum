import { Badge } from "@/components/ui/badge";
import type { AgentMessage as AgentMessageT } from "@/lib/types";

interface AgentMessageProps {
  message: AgentMessageT;
}

/**
 * One message body within an AgentCard. Renders the streaming text plus
 * citation chips. Structured output (Differential / NextTest / dict) is
 * rendered by the per-agent specialization in the visual pass.
 */
export function AgentMessage({ message }: AgentMessageProps) {
  return (
    <div className="space-y-2">
      <p className="text-sm whitespace-pre-wrap">{message.content}</p>
      {message.citations.length > 0 && (
        <div className="flex flex-wrap gap-1">
          {message.citations.map((c, idx) => (
            <Badge key={idx} variant="outline" title={c.title ?? c.source}>
              {c.source}
            </Badge>
          ))}
        </div>
      )}
    </div>
  );
}
