import { createFileRoute, Link } from "@tanstack/react-router";
import { Button } from "@/components/ui/button";
import {
  Brain,
  Languages,
  GraduationCap,
  BarChart3,
  Cpu,
  ArrowRight,
  Wand2,
  BookMarked,
  LayoutTemplate,
  FileQuestion,
  FileSearch,
  SlidersHorizontal,
} from "lucide-react";

export const Route = createFileRoute("/")({ component: Index });

function Index() {
  return (
    <div className="mx-auto max-w-7xl px-6">
      {/* Hero */}
      <section className="relative pt-20 pb-24 md:pt-28 md:pb-32">
        <div className="mx-auto max-w-3xl text-center">
          <span className="inline-flex items-center gap-2 rounded-full border border-border/60 bg-muted/40 px-3 py-1 text-xs font-medium text-muted-foreground">
            <Cpu className="h-3.5 w-3.5 text-accent" /> Intelligent AI-Powered Assessment Platform
          </span>
          <h1 className="mt-6 font-display text-5xl font-semibold leading-[1.05] tracking-tight md:text-7xl">
            Beyond question generation. <br />
            <span className="text-gradient">Outcome-based assessment.</span>
          </h1>
          <p className="mt-6 text-lg text-muted-foreground md:text-xl">
            Upload syllabus or notes. QGen.AI builds balanced question papers — classified by
            Bloom's taxonomy, mapped to Course Outcomes, blueprinted across units and difficulty,
            with analytics that close the loop for educators.
          </p>
          <div className="mt-9 flex flex-wrap items-center justify-center gap-3">
            <Link to="/generate">
              <Button size="lg" className="gap-2 bg-gradient-primary text-primary-foreground shadow-glow hover:opacity-95">
                <Wand2 className="h-5 w-5" /> Start generating <ArrowRight className="h-4 w-4" />
              </Button>
            </Link>
            <Link to="/analytics">
              <Button size="lg" variant="outline" className="gap-2">
                <BarChart3 className="h-5 w-5" /> View analytics
              </Button>
            </Link>
          </div>
        </div>

        {/* glow orb */}
        <div aria-hidden className="pointer-events-none absolute left-1/2 top-1/2 -z-10 h-[500px] w-[500px] -translate-x-1/2 -translate-y-1/2 rounded-full bg-primary/20 blur-[120px]" />
      </section>

      {/* Differentiators */}
      <section className="grid gap-5 pb-24 md:grid-cols-2 lg:grid-cols-3">
        {[
          { icon: Layers3, title: "Bloom's Taxonomy Classification", desc: "Every question tagged across all 6 cognitive levels — Remember to Create." },
          { icon: Target, title: "Course Outcome Mapping", desc: "Auto-map questions to CO1–CO6. NBA & OBE accreditation ready." },
          { icon: FileStack, title: "Blueprint Generation", desc: "Balanced papers: 30/50/20 difficulty split and unit-wise coverage you control." },
          { icon: BarChart3, title: "Educator Analytics", desc: "Bloom distribution, CO attainment, topic coverage, difficulty insights." },
          { icon: ListChecks, title: "Multiple Question Types", desc: "MCQs, descriptive, fill-in-the-blanks, and true/false — in one paper." },
          { icon: FileText, title: "PDF-to-Paper Pipeline", desc: "Upload → extract concepts → generate → classify → map → final paper." },
          { icon: Languages, title: "Multilingual", desc: "English, Hindi, Tamil, Telugu, Marathi out of the box." },
          { icon: Brain, title: "Adaptive Difficulty", desc: "Easy/Medium/Hard mix auto-tunes to total marks and learner level." },
        ].map((f) => (
          <div key={f.title} className="rounded-2xl bg-gradient-card p-6 shadow-card transition-transform hover:-translate-y-1">
            <div className="grid h-11 w-11 place-items-center rounded-xl bg-primary/15 text-primary">
              <f.icon className="h-5 w-5" />
            </div>
            <h3 className="mt-4 text-lg font-semibold">{f.title}</h3>
            <p className="mt-1 text-sm text-muted-foreground">{f.desc}</p>
          </div>
        ))}
      </section>
    </div>
  );
}
