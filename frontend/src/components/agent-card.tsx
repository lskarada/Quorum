import { AgentMessage as MessageBubble } from "@/components/agent-message";
import { AgentAvatar } from "@/components/agent-avatar";
import { cn } from "@/lib/utils";
import type { AgentMessage, AgentRole } from "@/lib/types";

interface AgentCardProps {
  message: AgentMessage;
}

const ROLE_LABEL: Record<AgentRole, string> = {
  hypothesis: "Hypothesis",
  test_chooser: "Test Chooser",
  challenger: "Challenger",
  stewardship: "Stewardship",
  checklist: "Checklist",
};

const ROLE_LEFT: Record<AgentRole, string> = {
  hypothesis: "border-l-agent-hypothesis",
  test_chooser: "border-l-agent-test-chooser",
  challenger: "border-l-agent-challenger",
  stewardship: "border-l-agent-stewardship",
  checklist: "border-l-agent-checklist",
};

const ROLE_TEXT: Record<AgentRole, string> = {
  hypothesis: "text-agent-hypothesis",
  test_chooser: "text-agent-test-chooser",
  challenger: "text-agent-challenger",
  stewardship: "text-[#a8780a]",
  checklist: "text-agent-checklist",
};

export function AgentCard({ message }: AgentCardProps) {
  return (
    <div className="flex gap-3" data-agent={message.role}>
      <AgentAvatar role={message.role} />
      <div
        className={cn(
          "flex-1 rounded-xl border border-l-[3px] border-line bg-surface-2 px-3.5 py-2.5",
          ROLE_LEFT[message.role],
        )}
      >
        <div className={cn("mb-1 text-[11px] font-extrabold uppercase tracking-wide", ROLE_TEXT[message.role])}>
          {ROLE_LABEL[message.role]}
        </div>
        <MessageBubble message={message} />
      </div>
    </div>
  );
}
