import { useState } from "react";
import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import { AlertTriangle, CheckCircle2, FileSearch } from "lucide-react";
import type { GeneratedPaper } from "@/lib/types";

const TYPE_LABEL = { mcq: "MCQ", fill: "Fill", descriptive: "Descriptive" } as const;

export function PaperView({ paper }: { paper: GeneratedPaper }) {
  const [visibleSources, setVisibleSources] = useState<Set<string>>(() => new Set());
  const report = paper.coverageReport;

  return (
    <div className="space-y-6">
      {report && <section aria-labelledby="paper-assessment-title" className="border-y border-border py-5">
        <div className="mb-4 flex items-start justify-between gap-4">
          <div>
            <h3 id="paper-assessment-title" className="font-semibold">Syllabus & blueprint assessment</h3>
            <p className="mt-1 text-sm text-muted-foreground">Estimated topic coverage and checks against the selected examination settings.</p>
          </div>
          <Badge variant={report.blueprint.satisfied ? "secondary" : "outline"}>
            {report.blueprint.satisfied ? "Blueprint satisfied" : "Review blueprint"}
          </Badge>
        </div>
        <div className="grid gap-4 sm:grid-cols-2 lg:grid-cols-4">
          <AssessmentStat label="Syllabus assessed" value={`${report.syllabusCoveragePercent}%`} />
          <AssessmentStat label="Difficulty" value={report.difficultyBalance.balanced ? "Balanced" : "Needs review"} />
          <AssessmentStat label="Paper marks" value={`${report.blueprint.actualTotalMarks} / ${report.blueprint.requestedTotalMarks}`} />
          <AssessmentStat label="Topics covered" value={`${report.topicsCovered.length}`} />
        </div>
        <p className="mt-3 text-xs text-muted-foreground">{report.coverageNote}</p>
        <div className="mt-4 grid gap-5 md:grid-cols-3">
          <AssessmentList title="Topics covered" empty="No topic labels available." items={report.topicsCovered.map((item) => `${item.topic} · ${item.questionCount} ${item.questionCount === 1 ? "question" : "questions"}`)} />
          <AssessmentList title="Important topics missing" empty="No uncovered extracted topics." items={report.importantTopicsMissing} />
          <AssessmentList title="Over-represented topics" empty="No topic is over-represented." items={report.overrepresentedTopics.map((item) => item.topic)} />
        </div>
        {!report.blueprint.satisfied && <ul className="mt-4 space-y-1 text-sm text-muted-foreground">
          {report.blueprint.issues.map((issue) => <li key={issue}>{issue}</li>)}
        </ul>}
      </section>}

      <div className="space-y-4">
      {paper.questions.map((q, i) => {
        const sourceVisible = visibleSources.has(q.id);
        const verification = q.evidenceStatus;
        return (
        <div key={q.id} className="rounded-xl bg-gradient-card p-5 shadow-card">
          <div className="mb-3 flex flex-wrap items-center gap-2 text-xs">
            <span className="font-mono text-muted-foreground">Q{i + 1}</span>
            <Badge variant="outline">{TYPE_LABEL[q.type]}</Badge>
            <Badge variant="outline" className="capitalize">{q.bloom}</Badge>
            <Badge variant="outline" className="capitalize">{q.difficulty}</Badge>
            {q.topic && <Badge variant="secondary">{q.topic}</Badge>}
            {q.co && <Badge className="bg-primary/10 text-primary hover:bg-primary/15">{q.co}</Badge>}
            {verification && <Badge variant={verification === "direct" ? "secondary" : "outline"}>
              {verification === "direct" ? "Source verified" : verification === "partial" ? "Partial evidence" : "Unsupported"}
            </Badge>}
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
          {(q.sourceEvidence || q.sourceReference || q.evidenceWarning) && <div className="mt-4 border-t border-border/60 pt-3">
            <Button
              type="button"
              size="sm"
              variant="outline"
              className="gap-2"
              aria-expanded={sourceVisible}
              onClick={() => setVisibleSources((current) => {
                const next = new Set(current);
                if (next.has(q.id)) next.delete(q.id);
                else next.add(q.id);
                return next;
              })}
            >
              <FileSearch className="h-4 w-4" />{sourceVisible ? "Hide source" : "Show source"}
            </Button>
            {sourceVisible && <div className="mt-3 space-y-3 text-sm">
              <p className="font-medium">Source reference: <span className="font-normal text-muted-foreground">{q.sourceReference ?? "Source material"}</span></p>
              {q.sourceEvidence && <blockquote className="border-l-2 border-primary/50 pl-3 leading-relaxed text-muted-foreground">{q.sourceEvidence}</blockquote>}
              <p><span className="font-medium">Expected answer:</span> <span className="text-muted-foreground">{q.answer}</span></p>
              {verification === "direct" && <p className="flex items-center gap-2 text-sm text-muted-foreground"><CheckCircle2 className="h-4 w-4 text-primary" />The answer is directly supported by the source.</p>}
              {verification === "partial" && <p className="flex items-start gap-2 text-sm text-muted-foreground"><AlertTriangle className="mt-0.5 h-4 w-4 shrink-0 text-primary" />{q.evidenceWarning ?? "The source provides partial support; review the answer."}</p>}
              {verification === "unsupported" && <p className="flex items-start gap-2 text-sm text-destructive"><AlertTriangle className="mt-0.5 h-4 w-4 shrink-0" />{q.evidenceWarning ?? "This question is not adequately grounded in the source. Review or remove it."}</p>}
            </div>}
          </div>}
        </div>
      );})}
      </div>
    </div>
  );
}

function AssessmentStat({ label, value }: { label: string; value: string }) {
  return <div className="border-l-2 border-primary/40 pl-3">
    <div className="text-xs text-muted-foreground">{label}</div>
    <div className="mt-1 font-semibold">{value}</div>
  </div>;
}

function AssessmentList({ title, empty, items }: { title: string; empty: string; items: string[] }) {
  return <div>
    <h4 className="text-sm font-medium">{title}</h4>
    {items.length ? <ul className="mt-2 space-y-1.5 text-sm text-muted-foreground">{items.map((item) => <li key={item}>{item}</li>)}</ul> : <p className="mt-2 text-sm text-muted-foreground">{empty}</p>}
  </div>;
}
