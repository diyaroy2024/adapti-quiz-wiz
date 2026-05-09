import { createFileRoute } from "@tanstack/react-router";
import { useEffect, useMemo, useState } from "react";
import { listPapers } from "@/lib/api";
import { BLOOM_LEVELS, LANGUAGES, type GeneratedPaper } from "@/lib/types";
import { BarChart, Bar, XAxis, YAxis, Tooltip, ResponsiveContainer, PieChart, Pie, Cell, RadialBarChart, RadialBar, Legend } from "recharts";
import { FileText, Brain, Layers3, Globe2 } from "lucide-react";

export const Route = createFileRoute("/analytics")({ component: AnalyticsPage });

function AnalyticsPage() {
  const [papers, setPapers] = useState<GeneratedPaper[]>([]);
  useEffect(() => setPapers(listPapers()), []);

  const stats = useMemo(() => compute(papers), [papers]);

  return (
    <div className="mx-auto max-w-7xl px-6 py-10">
      <div className="mb-8">
        <h1 className="text-3xl font-semibold md:text-4xl">Analytics</h1>
        <p className="mt-1 text-muted-foreground">Bloom coverage, type mix, difficulty across all generated papers.</p>
      </div>

      {papers.length === 0 ? (
        <div className="rounded-2xl border border-dashed border-border p-16 text-center text-muted-foreground">
          Generate at least one paper to see analytics.
        </div>
      ) : (
        <>
          <section className="mb-6 grid gap-4 md:grid-cols-4">
            <Stat icon={FileText} label="Papers" value={papers.length} />
            <Stat icon={Brain} label="Total questions" value={stats.totalQ} />
            <Stat icon={Layers3} label="Bloom levels used" value={stats.bloomCount} />
            <Stat icon={Globe2} label="Languages" value={stats.langCount} />
          </section>

          <section className="grid gap-6 lg:grid-cols-2">
            <Card title="Bloom's taxonomy distribution">
              <ResponsiveContainer width="100%" height={280}>
                <BarChart data={stats.bloomData}>
                  <XAxis dataKey="name" stroke="oklch(0.70 0.02 260)" fontSize={12} />
                  <YAxis stroke="oklch(0.70 0.02 260)" fontSize={12} />
                  <Tooltip contentStyle={tooltipStyle} />
                  <Bar dataKey="value" radius={[8, 8, 0, 0]}>
                    {stats.bloomData.map((_, i) => (
                      <Cell key={i} fill={`var(--chart-${(i % 5) + 1})`} />
                    ))}
                  </Bar>
                </BarChart>
              </ResponsiveContainer>
            </Card>

            <Card title="Question type mix">
              <ResponsiveContainer width="100%" height={280}>
                <PieChart>
                  <Pie data={stats.typeData} dataKey="value" nameKey="name" innerRadius={60} outerRadius={100} paddingAngle={4}>
                    {stats.typeData.map((_, i) => (
                      <Cell key={i} fill={`var(--chart-${(i % 5) + 1})`} />
                    ))}
                  </Pie>
                  <Legend />
                  <Tooltip contentStyle={tooltipStyle} />
                </PieChart>
              </ResponsiveContainer>
            </Card>

            <Card title="Difficulty distribution">
              <ResponsiveContainer width="100%" height={280}>
                <RadialBarChart innerRadius="30%" outerRadius="100%" data={stats.diffData} startAngle={90} endAngle={-270}>
                  <RadialBar background dataKey="value" cornerRadius={8} />
                  <Legend iconSize={10} />
                  <Tooltip contentStyle={tooltipStyle} />
                </RadialBarChart>
              </ResponsiveContainer>
            </Card>

            <Card title="Languages used">
              <ResponsiveContainer width="100%" height={280}>
                <BarChart data={stats.langData} layout="vertical">
                  <XAxis type="number" stroke="oklch(0.70 0.02 260)" fontSize={12} />
                  <YAxis dataKey="name" type="category" stroke="oklch(0.70 0.02 260)" fontSize={12} width={80} />
                  <Tooltip contentStyle={tooltipStyle} />
                  <Bar dataKey="value" radius={[0, 8, 8, 0]} fill="var(--accent)" />
                </BarChart>
              </ResponsiveContainer>
            </Card>
          </section>
        </>
      )}
    </div>
  );
}

const tooltipStyle = {
  background: "oklch(0.20 0.028 270)",
  border: "1px solid oklch(0.30 0.025 270)",
  borderRadius: 8,
  fontSize: 12,
};

function Stat({ icon: Icon, label, value }: { icon: any; label: string; value: number | string }) {
  return (
    <div className="rounded-2xl bg-gradient-card p-5 shadow-card">
      <div className="flex items-center gap-3">
        <div className="grid h-10 w-10 place-items-center rounded-lg bg-primary/15 text-primary">
          <Icon className="h-5 w-5" />
        </div>
        <div>
          <div className="text-xs uppercase tracking-wider text-muted-foreground">{label}</div>
          <div className="font-display text-2xl font-semibold">{value}</div>
        </div>
      </div>
    </div>
  );
}

function Card({ title, children }: { title: string; children: React.ReactNode }) {
  return (
    <div className="rounded-2xl bg-gradient-card p-6 shadow-card">
      <h3 className="mb-4 font-semibold">{title}</h3>
      {children}
    </div>
  );
}

function compute(papers: GeneratedPaper[]) {
  const all = papers.flatMap((p) => p.questions.map((q) => ({ q, lang: p.config.language })));
  const bloomCounts: Record<string, number> = {};
  const typeCounts: Record<string, number> = { mcq: 0, fill: 0, descriptive: 0 };
  const diffCounts: Record<string, number> = { easy: 0, medium: 0, hard: 0 };
  const langCounts: Record<string, number> = {};
  all.forEach(({ q, lang }) => {
    bloomCounts[q.bloom] = (bloomCounts[q.bloom] ?? 0) + 1;
    typeCounts[q.type] = (typeCounts[q.type] ?? 0) + 1;
    diffCounts[q.difficulty] = (diffCounts[q.difficulty] ?? 0) + 1;
    langCounts[lang] = (langCounts[lang] ?? 0) + 1;
  });

  return {
    totalQ: all.length,
    bloomCount: Object.values(bloomCounts).filter(Boolean).length,
    langCount: Object.keys(langCounts).length,
    bloomData: BLOOM_LEVELS.map((b) => ({ name: b.label, value: bloomCounts[b.id] ?? 0 })),
    typeData: [
      { name: "MCQ", value: typeCounts.mcq },
      { name: "Fill", value: typeCounts.fill },
      { name: "Descriptive", value: typeCounts.descriptive },
    ].filter((d) => d.value > 0),
    diffData: [
      { name: "Easy", value: diffCounts.easy, fill: "var(--chart-4)" },
      { name: "Medium", value: diffCounts.medium, fill: "var(--chart-3)" },
      { name: "Hard", value: diffCounts.hard, fill: "var(--chart-5)" },
    ],
    langData: LANGUAGES.filter((l) => langCounts[l.id]).map((l) => ({ name: l.label, value: langCounts[l.id] })),
  };
}
