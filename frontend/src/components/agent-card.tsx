import { AgentMessage as MessageBubble } from "@/components/agent-message";
import { Badge } from "@/components/ui/badge";
import { Card } from "@/components/ui/card";
import { cn } from "@/lib/utils";
import type { AgentMessage, AgentRole } from "@/lib/types";

interface AgentCardProps {
  message: AgentMessage;
}

const ROLE_LABEL: Record<AgentRole, string> = {
  hypothesis: "Dr. Hypothesis",
  test_chooser: "Dr. Test-Chooser",
  challenger: "Dr. Challenger",
  stewardship: "Dr. Stewardship",
  checklist: "Dr. Checklist",
};

const ROLE_BORDER: Record<AgentRole, string> = {
  hypothesis: "border-l-agent-hypothesis",
  test_chooser: "border-l-agent-test-chooser",
  challenger: "border-l-agent-challenger",
  stewardship: "border-l-agent-stewardship",
  checklist: "border-l-agent-checklist",
};

export function AgentCard({ message }: AgentCardProps) {
  return (
    <Card className={cn("p-4 border-l-4", ROLE_BORDER[message.role])}>
      <div className="flex items-center justify-between mb-2">
        <span className="font-semibold">{ROLE_LABEL[message.role]}</span>
        <Badge variant="secondary">Round {message.iteration + 1}</Badge>
      </div>
      <MessageBubble message={message} />
    </Card>
  );
}
