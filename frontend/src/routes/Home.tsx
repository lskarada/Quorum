import { Link } from "react-router-dom";
import { Button } from "@/components/ui/button";
import { TopBar } from "@/components/top-bar";

const AGENTS: { name: string; color: string }[] = [
  { name: "Hypothesis", color: "hsl(217 91% 60%)" },
  { name: "Test chooser", color: "hsl(160 84% 39%)" },
  { name: "Challenger", color: "hsl(0 84% 60%)" },
  { name: "Stewardship", color: "hsl(43 96% 56%)" },
  { name: "Checklist", color: "hsl(280 91% 60%)" },
];

export default function Home() {
  return (
    <main className="mx-auto flex min-h-screen max-w-[1280px] flex-col gap-[18px] bg-background p-4 text-foreground">
      <TopBar />

      <section className="flex flex-1 flex-col items-center justify-center px-4 text-center">
        <div className="flex max-w-3xl flex-col items-center gap-6">
          <span
            className="h-14 w-14 rounded-2xl shadow-card-2"
            style={{
              background:
                "linear-gradient(135deg, hsl(217 91% 60%), hsl(280 91% 60%))",
            }}
          />
          <h1 className="text-5xl font-extrabold tracking-tight">Quorum</h1>
          <p className="text-xl font-semibold text-ink-2">
            Open-source diagnostic deliberation for clinical AI agents.
          </p>
          <p className="max-w-2xl text-base text-muted-foreground">
            Five specialist agents debate a clinical case in the open — you
            watch the deliberation stream live, ranked differential and cited
            next-test recommendation included.
          </p>

          <ul className="flex flex-wrap items-center justify-center gap-x-5 gap-y-2 pt-1">
            {AGENTS.map((a) => (
              <li
                key={a.name}
                className="flex items-center gap-2 text-[12.5px] font-semibold text-ink-2"
              >
                <span
                  className="h-2.5 w-2.5 rounded-full"
                  style={{ background: a.color }}
                />
                {a.name}
              </li>
            ))}
          </ul>

          <div className="flex flex-wrap items-center justify-center gap-3 pt-4">
            <Button asChild size="lg">
              <Link to="/diagnose">Try the demo</Link>
            </Button>
            <Button asChild size="lg" variant="outline">
              <Link to="/compare">Compare panels</Link>
            </Button>
            <Button asChild size="lg" variant="outline">
              <Link to="/evidence">Evidence &amp; clinical grounding</Link>
            </Button>
          </div>
        </div>
      </section>
    </main>
  );
}
