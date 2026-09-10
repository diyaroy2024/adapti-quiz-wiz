import { createFileRoute, Link } from "@tanstack/react-router";
import { useEffect, useState } from "react";
import { listPapers, deletePaper, fetchPapers, deletePaperRemote } from "@/lib/api";
import { useAuth } from "@/lib/auth";
import { toast } from "sonner";
import type { GeneratedPaper } from "@/lib/types";
import { Button } from "@/components/ui/button";
import { Badge } from "@/components/ui/badge";
import { FileText, Trash2, Wand2 } from "lucide-react";
import { PaperView } from "@/components/PaperView";

export const Route = createFileRoute("/papers")({ component: PapersPage });

function PapersPage() {
  const { user } = useAuth();
  const [papers, setPapers] = useState<GeneratedPaper[]>([]);
  const [open, setOpen] = useState<string | null>(null);

  useEffect(() => {
    if (user) {
      fetchPapers()
        .then(setPapers)
        .catch((e) => {
          toast.error(e.message ?? "Could not load your saved papers");
          setPapers(listPapers());
        });
    } else {
      setPapers(listPapers());
    }
  }, [user]);

  async function remove(id: string) {
    if (user) {
      try {
        await deletePaperRemote(id);
      } catch (e: any) {
        toast.error(e.message ?? "Could not delete that paper");
        return;
      }
    }
    deletePaper(id);
    setPapers((prev) => prev.filter((p) => p.id !== id));
  }

  return (
    <div className="mx-auto max-w-7xl px-6 py-10">
      <div className="mb-8 flex items-end justify-between">
        <div>
          <h1 className="text-3xl font-semibold md:text-4xl">Saved papers</h1>
          <p className="mt-1 text-muted-foreground">{user ? `Saved to your account (${user.email}).` : "Stored in this browser. Sign in to keep them in your account."}</p>
        </div>
        <Link to="/generate">
          <Button className="gap-2 bg-gradient-primary text-primary-foreground"><Wand2 className="h-4 w-4" />New paper</Button>
        </Link>
      </div>

      {papers.length === 0 ? (
        <div className="rounded-2xl border border-dashed border-border p-16 text-center text-muted-foreground">
          No papers yet. Generate your first one.
        </div>
      ) : (
        <div className="grid gap-4">
          {papers.map((p) => (
            <div key={p.id} className="rounded-2xl bg-gradient-card p-5 shadow-card">
              <div className="flex items-start gap-4">
                <div className="grid h-12 w-12 place-items-center rounded-xl bg-primary/15 text-primary">
                  <FileText className="h-5 w-5" />
                </div>
                <div className="flex-1">
                  <h3 className="font-semibold">{p.title}</h3>
                  <p className="mt-0.5 text-xs text-muted-foreground">
                    {new Date(p.createdAt).toLocaleString()} · {p.questions.length} questions · {p.config.totalMarks} marks
                  </p>
                  <div className="mt-2 flex flex-wrap gap-1.5">
                    {p.config.bloomLevels.map((b) => <Badge key={b} variant="outline" className="capitalize">{b}</Badge>)}
                  </div>
                </div>
                <div className="flex gap-2">
                  <Button size="sm" variant="outline" onClick={() => setOpen(open === p.id ? null : p.id)}>
                    {open === p.id ? "Hide" : "View"}
                  </Button>
                  <Button size="sm" variant="ghost" onClick={() => remove(p.id)}>
                    <Trash2 className="h-4 w-4" />
                  </Button>
                </div>
              </div>
              {open === p.id && <div className="mt-5"><PaperView paper={p} /></div>}
            </div>
          ))}
        </div>
      )}
    </div>
  );
}
