import { Badge } from "@/components/ui/badge";
import type { GeneratedPaper } from "@/lib/types";

const TYPE_LABEL = { mcq: "MCQ", fill: "Fill", descriptive: "Descriptive" } as const;

export function PaperView({ paper }: { paper: GeneratedPaper }) {
  return (
    <div className="space-y-4">
      {paper.questions.map((q, i) => (
        <div key={q.id} className="rounded-xl bg-gradient-card p-5 shadow-card">
          <div className="mb-3 flex flex-wrap items-center gap-2 text-xs">
            <span className="font-mono text-muted-foreground">Q{i + 1}</span>
            <Badge variant="outline">{TYPE_LABEL[q.type]}</Badge>
            <Badge variant="outline" className="capitalize">{q.bloom}</Badge>
            <Badge variant="outline" className="capitalize">{q.difficulty}</Badge>
            <span className="ml-auto font-mono text-muted-foreground">{q.marks} marks</span>
          </div>
          <p className="text-base leading-relaxed">{q.question}</p>
          {q.options && (
            <ol className="mt-3 grid gap-2 text-sm">
              {q.options.map((o, j) => (
                <li key={j} className="flex items-start gap-2 rounded-md border border-border/50 bg-background/40 px-3 py-2">
                  <span className="font-mono text-muted-foreground">{String.fromCharCode(65 + j)}.</span>
                  <span>{o}</span>
                </li>
              ))}
            </ol>
          )}
          <details className="mt-3 text-sm">
            <summary className="cursor-pointer text-muted-foreground hover:text-foreground">Show answer</summary>
            <p className="mt-2 rounded-md border border-accent/30 bg-accent/5 px-3 py-2 text-accent">{q.answer}</p>
          </details>
        </div>
      ))}
    </div>
  );
}
