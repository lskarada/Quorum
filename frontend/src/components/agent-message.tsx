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
      <p className="whitespace-pre-wrap text-[13px] leading-relaxed text-ink-2">{message.content}</p>
      {message.citations && message.citations.length > 0 && (
        <div className="flex flex-wrap gap-1.5">
          {message.citations.map((c, idx) => (
            <span
              key={idx}
              title={c.title ?? c.source}
              className="inline-flex items-center rounded-full border border-line-strong bg-surface-2 px-2 py-0.5 font-mono text-[11px] font-medium text-muted-foreground"
            >
              {c.source}
            </span>
          ))}
        </div>
      )}
    </div>
  );
}
