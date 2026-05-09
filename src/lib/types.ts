export type BloomLevel =
  | "remember"
  | "understand"
  | "apply"
  | "analyze"
  | "evaluate"
  | "create";

export const BLOOM_LEVELS: { id: BloomLevel; label: string; color: string }[] = [
  { id: "remember", label: "Remember", color: "var(--chart-1)" },
  { id: "understand", label: "Understand", color: "var(--chart-2)" },
  { id: "apply", label: "Apply", color: "var(--chart-3)" },
  { id: "analyze", label: "Analyze", color: "var(--chart-4)" },
  { id: "evaluate", label: "Evaluate", color: "var(--chart-5)" },
  { id: "create", label: "Create", color: "var(--primary)" },
];

export type Language = "en" | "hi" | "ta" | "te" | "mr";
export const LANGUAGES: { id: Language; label: string; native: string }[] = [
  { id: "en", label: "English", native: "English" },
  { id: "hi", label: "Hindi", native: "हिन्दी" },
  { id: "ta", label: "Tamil", native: "தமிழ்" },
  { id: "te", label: "Telugu", native: "తెలుగు" },
  { id: "mr", label: "Marathi", native: "मराठी" },
];

export type QuestionType = "mcq" | "fill" | "descriptive";
export type Difficulty = "easy" | "medium" | "hard";

export interface GeneratedQuestion {
  id: string;
  type: QuestionType;
  bloom: BloomLevel;
  difficulty: Difficulty;
  marks: number;
  question: string;
  options?: string[];
  answer: string;
  keywords?: string[];
}

export interface PaperConfig {
  language: Language;
  totalMarks: number;
  bloomLevels: BloomLevel[];
  types: QuestionType[];
  // adaptive split: percentages summing to 100
  difficultyMix: { easy: number; medium: number; hard: number };
  topicHint?: string;
}

export interface GeneratedPaper {
  id: string;
  title: string;
  createdAt: string;
  config: PaperConfig;
  questions: GeneratedQuestion[];
  sourcePreview: string;
}
