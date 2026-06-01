import type { AgentRole } from "@/lib/types";

const INITIAL: Record<AgentRole, string> = {
  hypothesis: "H",
  test_chooser: "T",
  challenger: "C",
  stewardship: "S",
  checklist: "K",
};
const BG: Record<AgentRole, string> = {
  hypothesis: "bg-agent-hypothesis",
  test_chooser: "bg-agent-test-chooser",
  challenger: "bg-agent-challenger",
  stewardship: "bg-agent-stewardship",
  checklist: "bg-agent-checklist",
};
const FG: Record<AgentRole, string> = {
  hypothesis: "text-white",
  test_chooser: "text-white",
  challenger: "text-white",
  stewardship: "text-[#3a2c00]",
  checklist: "text-white",
};

export function AgentAvatar({ role }: { role: AgentRole }) {
  return (
    <span
      aria-hidden
      className={`flex h-[30px] w-[30px] flex-none items-center justify-center rounded-[9px] text-[11px] font-extrabold ${BG[role]} ${FG[role]}`}
    >
      {INITIAL[role]}
    </span>
  );
}
