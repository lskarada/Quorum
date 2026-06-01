export function TypingIndicator() {
  return (
    <span className="inline-flex items-center gap-[3px] align-middle" aria-label="thinking">
      <i className="h-[5px] w-[5px] rounded-full bg-faint animate-blink" />
      <i className="h-[5px] w-[5px] rounded-full bg-faint animate-blink [animation-delay:.2s]" />
      <i className="h-[5px] w-[5px] rounded-full bg-faint animate-blink [animation-delay:.4s]" />
    </span>
  );
}
