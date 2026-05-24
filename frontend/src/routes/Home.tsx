import { Link } from "react-router-dom";
import { Button } from "@/components/ui/button";

export default function Home() {
  return (
    <main className="min-h-screen flex flex-col items-center justify-center px-4">
      <div className="max-w-3xl text-center space-y-6">
        <h1 className="text-5xl font-bold tracking-tight">Quorum</h1>
        <p className="text-xl text-muted-foreground">
          Open-source diagnostic deliberation for clinical AI agents.
        </p>
        <p className="text-base text-muted-foreground max-w-2xl mx-auto">
          {/* TODO: refine copy */}
          Five specialist agents deliberate on a clinical case. Watch the debate, see the
          ranked differential, get a cited next-test recommendation.
        </p>
        <div className="pt-4 flex flex-wrap items-center justify-center gap-3">
          <Button asChild size="lg">
            <Link to="/diagnose">Try the demo</Link>
          </Button>
          <Button asChild size="lg" variant="outline">
            <Link to="/compare">Compare panels</Link>
          </Button>
        </div>
      </div>
    </main>
  );
}
