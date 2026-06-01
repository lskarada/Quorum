import { motion, useReducedMotion } from "framer-motion";

interface ConfidenceRingProps {
  value: number; // 0..1
  size?: number;
  label?: string;
}

const HYP = "hsl(217 91% 60%)";

export function ConfidenceRing({ value, size = 62, label }: ConfidenceRingProps) {
  const pct = Math.round(Math.max(0, Math.min(1, value)) * 100);
  const reduce = useReducedMotion();
  const inner = size - 16;
  return (
    <div
      role="img"
      aria-label={label ?? `Confidence ${pct} percent`}
      style={{
        width: size,
        height: size,
        borderRadius: "50%",
        background: `conic-gradient(${HYP} 0 ${pct}%, #e8eef6 ${pct}% 100%)`,
        display: "flex",
        alignItems: "center",
        justifyContent: "center",
        flex: "none",
      }}
    >
      <div
        style={{
          width: inner,
          height: inner,
          borderRadius: "50%",
          background: "#fff",
          display: "flex",
          alignItems: "center",
          justifyContent: "center",
        }}
      >
        <motion.span
          className="font-mono font-extrabold text-agent-hypothesis"
          style={{ fontSize: size * 0.24 }}
          initial={reduce ? false : { opacity: 0 }}
          animate={{ opacity: 1 }}
        >
          {pct}%
        </motion.span>
      </div>
    </div>
  );
}
