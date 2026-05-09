import { createFileRoute } from "@tanstack/react-router";
import { useState } from "react";
import { toast } from "sonner";
import { Button } from "@/components/ui/button";
import { Textarea } from "@/components/ui/textarea";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import { Slider } from "@/components/ui/slider";
import { Checkbox } from "@/components/ui/checkbox";
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from "@/components/ui/select";
import { Tabs, TabsContent, TabsList, TabsTrigger } from "@/components/ui/tabs";
import { Badge } from "@/components/ui/badge";
import { Upload, Wand2, FileText, Loader2, Download } from "lucide-react";
import { BLOOM_LEVELS, LANGUAGES, type BloomLevel, type Language, type PaperConfig, type QuestionType, type GeneratedPaper } from "@/lib/types";
import { extractText } from "@/lib/file-extract";
import { generatePaper } from "@/lib/api";
import { PaperView } from "@/components/PaperView";

export const Route = createFileRoute("/generate")({ component: GeneratePage });

function GeneratePage() {
  const [title, setTitle] = useState("Mid-semester Exam");
  const [text, setText] = useState("");
  const [fileName, setFileName] = useState<string | null>(null);
  const [language, setLanguage] = useState<Language>("en");
  const [totalMarks, setTotalMarks] = useState(50);
  const [bloom, setBloom] = useState<BloomLevel[]>(["remember", "understand", "apply", "analyze"]);
  const [types, setTypes] = useState<QuestionType[]>(["mcq", "fill", "descriptive"]);
  const [easy, setEasy] = useState(40);
  const [medium, setMedium] = useState(40);
  const [generating, setGenerating] = useState(false);
  const [paper, setPaper] = useState<GeneratedPaper | null>(null);

  const hard = Math.max(0, 100 - easy - medium);

  async function onFile(f: File) {
    try {
      setFileName(f.name);
      toast.info(`Parsing ${f.name}…`);
      const t = await extractText(f);
      setText(t);
      toast.success(`Extracted ${t.length.toLocaleString()} characters`);
    } catch (e: any) {
      toast.error(e.message ?? "Failed to read file");
    }
  }

  async function onGenerate() {
    if (text.trim().length < 50) {
      toast.error("Add at least 50 characters of source text");
      return;
    }
    if (bloom.length === 0 || types.length === 0) {
      toast.error("Pick at least one Bloom level and one question type");
      return;
    }
    setGenerating(true);
    try {
      const config: PaperConfig = {
        language,
        totalMarks,
        bloomLevels: bloom,
        types,
        difficultyMix: { easy, medium, hard },
      };
      const p = await generatePaper(text, config, title);
      setPaper(p);
      toast.success(`Generated ${p.questions.length} questions`);
    } catch (e: any) {
      toast.error(e.message ?? "Generation failed");
    } finally {
      setGenerating(false);
    }
  }

  function toggle<T>(arr: T[], v: T, set: (a: T[]) => void) {
    set(arr.includes(v) ? arr.filter((x) => x !== v) : [...arr, v]);
  }

  return (
    <div className="mx-auto max-w-7xl px-6 py-10">
      <div className="mb-8">
        <h1 className="text-3xl font-semibold md:text-4xl">Generate a paper</h1>
        <p className="mt-1 text-muted-foreground">Provide source material, set constraints, generate.</p>
      </div>

      <div className="grid gap-6 lg:grid-cols-[minmax(0,1.2fr)_minmax(0,1fr)]">
        {/* LEFT — Source + config */}
        <div className="space-y-6">
          <div className="rounded-2xl bg-gradient-card p-6 shadow-card">
            <Label htmlFor="title">Paper title</Label>
            <Input id="title" value={title} onChange={(e) => setTitle(e.target.value)} className="mt-2" />
          </div>

          <div className="rounded-2xl bg-gradient-card p-6 shadow-card">
            <Tabs defaultValue="text">
              <TabsList className="mb-4">
                <TabsTrigger value="text"><FileText className="mr-2 h-4 w-4" />Paste text</TabsTrigger>
                <TabsTrigger value="file"><Upload className="mr-2 h-4 w-4" />Upload PDF / DOCX</TabsTrigger>
              </TabsList>
              <TabsContent value="text">
                <Textarea
                  value={text}
                  onChange={(e) => setText(e.target.value)}
                  placeholder="Paste syllabus, lecture notes, chapter excerpt…"
                  className="min-h-[260px] resize-y font-mono text-sm"
                />
              </TabsContent>
              <TabsContent value="file">
                <label className="flex min-h-[220px] cursor-pointer flex-col items-center justify-center gap-2 rounded-xl border-2 border-dashed border-border bg-background/40 p-6 text-center transition-colors hover:border-primary/60 hover:bg-primary/5">
                  <Upload className="h-8 w-8 text-muted-foreground" />
                  <div className="text-sm font-medium">{fileName ?? "Click to upload .pdf, .docx, or .txt"}</div>
                  <div className="text-xs text-muted-foreground">Parsed in your browser — no upload</div>
                  <input
                    type="file"
                    accept=".pdf,.docx,.txt,application/pdf"
                    className="hidden"
                    onChange={(e) => e.target.files?.[0] && onFile(e.target.files[0])}
                  />
                </label>
                {text && (
                  <p className="mt-3 text-xs text-muted-foreground">
                    {text.length.toLocaleString()} characters extracted.
                  </p>
                )}
              </TabsContent>
            </Tabs>
          </div>
        </div>

        {/* RIGHT — Settings */}
        <div className="space-y-6">
          <div className="rounded-2xl bg-gradient-card p-6 shadow-card">
            <h3 className="mb-4 font-semibold">Constraints</h3>

            <div className="grid grid-cols-2 gap-4">
              <div>
                <Label>Language</Label>
                <Select value={language} onValueChange={(v) => setLanguage(v as Language)}>
                  <SelectTrigger className="mt-2"><SelectValue /></SelectTrigger>
                  <SelectContent>
                    {LANGUAGES.map((l) => (
                      <SelectItem key={l.id} value={l.id}>{l.label} · {l.native}</SelectItem>
                    ))}
                  </SelectContent>
                </Select>
              </div>
              <div>
                <Label>Total marks</Label>
                <Input type="number" min={10} max={200} value={totalMarks}
                  onChange={(e) => setTotalMarks(parseInt(e.target.value) || 50)} className="mt-2" />
              </div>
            </div>

            <div className="mt-5">
              <Label className="mb-2 block">Bloom's taxonomy levels</Label>
              <div className="flex flex-wrap gap-2">
                {BLOOM_LEVELS.map((b) => {
                  const active = bloom.includes(b.id);
                  return (
                    <button
                      key={b.id}
                      type="button"
                      onClick={() => toggle(bloom, b.id, setBloom)}
                      className={`rounded-full border px-3 py-1.5 text-xs font-medium transition-colors ${
                        active
                          ? "border-primary bg-primary/15 text-primary"
                          : "border-border bg-background/40 text-muted-foreground hover:text-foreground"
                      }`}
                    >
                      {b.label}
                    </button>
                  );
                })}
              </div>
            </div>

            <div className="mt-5">
              <Label className="mb-2 block">Question types</Label>
              <div className="grid gap-2">
                {([
                  { id: "mcq", label: "Multiple Choice (MCQ)" },
                  { id: "fill", label: "Fill in the Blanks" },
                  { id: "descriptive", label: "Descriptive / Long answer" },
                ] as { id: QuestionType; label: string }[]).map((t) => (
                  <label key={t.id} className="flex items-center gap-3 rounded-md border border-border/60 bg-background/40 px-3 py-2 text-sm">
                    <Checkbox checked={types.includes(t.id)} onCheckedChange={() => toggle(types, t.id, setTypes)} />
                    {t.label}
                  </label>
                ))}
              </div>
            </div>

            <div className="mt-6 space-y-4 rounded-xl border border-border/60 p-4">
              <div className="flex items-center justify-between">
                <Label className="text-sm">Adaptive difficulty mix</Label>
                <span className="font-mono text-xs text-muted-foreground">E {easy} · M {medium} · H {hard}</span>
              </div>
              <div>
                <div className="mb-1 flex justify-between text-xs"><span>Easy</span><span>{easy}%</span></div>
                <Slider value={[easy]} onValueChange={([v]) => setEasy(Math.min(v, 100 - medium))} max={100} step={5} />
              </div>
              <div>
                <div className="mb-1 flex justify-between text-xs"><span>Medium</span><span>{medium}%</span></div>
                <Slider value={[medium]} onValueChange={([v]) => setMedium(Math.min(v, 100 - easy))} max={100} step={5} />
              </div>
              <div>
                <div className="mb-1 flex justify-between text-xs"><span>Hard (auto)</span><span>{hard}%</span></div>
                <div className="h-2 rounded-full bg-muted">
                  <div className="h-full rounded-full bg-gradient-primary" style={{ width: `${hard}%` }} />
                </div>
              </div>
            </div>
          </div>

          <Button
            size="lg"
            disabled={generating}
            onClick={onGenerate}
            className="w-full gap-2 bg-gradient-primary text-primary-foreground shadow-glow"
          >
            {generating ? <Loader2 className="h-5 w-5 animate-spin" /> : <Wand2 className="h-5 w-5" />}
            {generating ? "Generating…" : "Generate paper"}
          </Button>
        </div>
      </div>

      {paper && (
        <div className="mt-12">
          <div className="mb-4 flex items-center justify-between">
            <div>
              <h2 className="text-2xl font-semibold">{paper.title}</h2>
              <div className="mt-1 flex flex-wrap gap-2">
                <Badge variant="secondary">{paper.questions.length} questions</Badge>
                <Badge variant="secondary">{paper.config.totalMarks} marks</Badge>
                <Badge variant="secondary">{LANGUAGES.find((l) => l.id === paper.config.language)?.label}</Badge>
              </div>
            </div>
            <Button variant="outline" onClick={() => downloadPaper(paper)} className="gap-2">
              <Download className="h-4 w-4" /> Download
            </Button>
          </div>
          <PaperView paper={paper} />
        </div>
      )}
    </div>
  );
}

function downloadPaper(p: GeneratedPaper) {
  const lines: string[] = [];
  lines.push(p.title);
  lines.push(`Total marks: ${p.config.totalMarks}`);
  lines.push("");
  p.questions.forEach((q, i) => {
    lines.push(`Q${i + 1}. [${q.bloom} · ${q.difficulty} · ${q.marks}m] ${q.question}`);
    if (q.options) q.options.forEach((o, j) => lines.push(`   ${String.fromCharCode(65 + j)}. ${o}`));
    lines.push(`Ans: ${q.answer}`);
    lines.push("");
  });
  const blob = new Blob([lines.join("\n")], { type: "text/plain" });
  const a = document.createElement("a");
  a.href = URL.createObjectURL(blob);
  a.download = `${p.title.replace(/\s+/g, "_")}.txt`;
  a.click();
}
