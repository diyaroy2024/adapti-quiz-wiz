import type { GeneratedPaper, PaperConfig, GeneratedQuestion } from "./types";

const STORAGE_KEY = "qpgen_backend_url";
const PAPERS_KEY = "qpgen_papers";

export function getBackendUrl(): string {
  if (typeof window === "undefined") return "";
  return localStorage.getItem(STORAGE_KEY) ?? "";
}
export function setBackendUrl(url: string) {
  localStorage.setItem(STORAGE_KEY, url.trim());
}

/** POST {text, config} -> GeneratedPaper. Falls back to mock generator. */
export async function generatePaper(
  source: string,
  config: PaperConfig,
  title: string,
): Promise<GeneratedPaper> {
  const url = getBackendUrl();
  if (url) {
    const res = await fetch(`${url.replace(/\/$/, "")}/generate`, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ text: source, config, title }),
    });
    if (!res.ok) throw new Error(`Backend ${res.status}: ${await res.text()}`);
    const paper = (await res.json()) as GeneratedPaper;
    savePaper(paper);
    return paper;
  }
  // Local mock — deterministic-ish demo content
  const paper = mockGenerate(source, config, title);
  savePaper(paper);
  return paper;
}

export function listPapers(): GeneratedPaper[] {
  if (typeof window === "undefined") return [];
  try {
    return JSON.parse(localStorage.getItem(PAPERS_KEY) ?? "[]");
  } catch {
    return [];
  }
}
export function savePaper(p: GeneratedPaper) {
  const all = listPapers();
  all.unshift(p);
  localStorage.setItem(PAPERS_KEY, JSON.stringify(all.slice(0, 50)));
}
export function deletePaper(id: string) {
  localStorage.setItem(
    PAPERS_KEY,
    JSON.stringify(listPapers().filter((p) => p.id !== id)),
  );
}

// -------------- mock generator (offline/demo) --------------
function mockGenerate(
  source: string,
  config: PaperConfig,
  title: string,
): GeneratedPaper {
  const sentences = source
    .replace(/\s+/g, " ")
    .split(/[.!?]+/)
    .map((s) => s.trim())
    .filter((s) => s.length > 30)
    .slice(0, 40);

  const keywords = extractKeywords(source).slice(0, 30);
  const questions: GeneratedQuestion[] = [];
  const targetCount = Math.max(5, Math.min(20, Math.floor(config.totalMarks / 2)));
  const { easy, medium, hard } = config.difficultyMix;
  const bag: ("easy" | "medium" | "hard")[] = [];
  for (let i = 0; i < easy; i++) bag.push("easy");
  for (let i = 0; i < medium; i++) bag.push("medium");
  for (let i = 0; i < hard; i++) bag.push("hard");

  for (let i = 0; i < targetCount; i++) {
    const type = config.types[i % config.types.length];
    const bloom = config.bloomLevels[i % config.bloomLevels.length];
    const difficulty = bag[Math.floor((i / targetCount) * bag.length)] ?? "medium";
    const marks = difficulty === "easy" ? 1 : difficulty === "medium" ? 3 : 5;
    const sent = sentences[i % Math.max(1, sentences.length)] ?? "the given concept";
    const kw = keywords[i % Math.max(1, keywords.length)] ?? "concept";

    if (type === "mcq") {
      const distractors = keywords
        .filter((k) => k !== kw)
        .slice(0, 3)
        .concat(["None of the above", "All of the above"])
        .slice(0, 3);
      questions.push({
        id: crypto.randomUUID(),
        type,
        bloom,
        difficulty,
        marks,
        question: translate(`Which term best relates to: "${truncate(sent, 110)}"?`, config.language),
        options: shuffle([kw, ...distractors]),
        answer: kw,
      });
    } else if (type === "fill") {
      const blanked = sent.replace(new RegExp(`\\b${kw}\\b`, "i"), "_____");
      questions.push({
        id: crypto.randomUUID(),
        type,
        bloom,
        difficulty,
        marks,
        question: translate(blanked === sent ? `Fill in the blank: ${truncate(sent, 130)} _____` : blanked, config.language),
        answer: kw,
      });
    } else {
      const verb = bloomVerb(bloom);
      questions.push({
        id: crypto.randomUUID(),
        type,
        bloom,
        difficulty,
        marks,
        question: translate(`${verb} the concept of "${kw}" with reference to: ${truncate(sent, 140)}`, config.language),
        answer: `Refer to source. Key term: ${kw}.`,
        keywords: [kw],
      });
    }
  }

  return {
    id: crypto.randomUUID(),
    title: title || "Untitled Paper",
    createdAt: new Date().toISOString(),
    config,
    questions,
    sourcePreview: source.slice(0, 240),
  };
}

function truncate(s: string, n: number) {
  return s.length > n ? s.slice(0, n - 1) + "…" : s;
}
function shuffle<T>(arr: T[]) {
  const a = [...arr];
  for (let i = a.length - 1; i > 0; i--) {
    const j = Math.floor(Math.random() * (i + 1));
    [a[i], a[j]] = [a[j], a[i]];
  }
  return a;
}
function extractKeywords(text: string): string[] {
  const stop = new Set(
    "the a an and or of to in is are was were be been being for on with as by at from this that these those it its their our your we you they i he she has have had do does did not no so if then than which who whom whose what where when why how".split(
      " ",
    ),
  );
  const counts = new Map<string, number>();
  text
    .toLowerCase()
    .replace(/[^a-z\s-]/g, " ")
    .split(/\s+/)
    .filter((w) => w.length > 4 && !stop.has(w))
    .forEach((w) => counts.set(w, (counts.get(w) ?? 0) + 1));
  return [...counts.entries()].sort((a, b) => b[1] - a[1]).map((e) => e[0]);
}
function bloomVerb(b: string) {
  return {
    remember: "Define",
    understand: "Explain",
    apply: "Apply",
    analyze: "Analyze",
    evaluate: "Evaluate",
    create: "Design",
  }[b] ?? "Discuss";
}
function translate(s: string, lang: string) {
  if (lang === "en") return s;
  const tag = { hi: "[HI]", ta: "[TA]", te: "[TE]", mr: "[MR]" }[lang] ?? "";
  return `${tag} ${s}`; // placeholder — backend will return translated text
}
