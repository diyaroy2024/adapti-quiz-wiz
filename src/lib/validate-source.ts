/**
 * Source-material sanity checks.
 *
 * Rejects input that cannot possibly yield meaningful questions: a single word
 * pasted repeatedly, keyboard mashing, symbol soup, or a few disconnected words
 * with no sentence structure.
 */

export type SourceCheck = { ok: true } | { ok: false; reason: string };

const STOP = new Set(
  "the a an and or of to in is are was were be been being for on with as by at from this that these those it its their our your we you they has have had do does did not no so if then than which who whom whose what where when why how".split(
    " ",
  ),
);

export function validateSource(raw: string): SourceCheck {
  const text = raw.replace(/\s+/g, " ").trim();

  if (text.length < 120) {
    return {
      ok: false,
      reason:
        "The source material is too short. Paste at least a few sentences of relevant study content (about 120 characters).",
    };
  }

  const letters = (text.match(/[A-Za-z\u0900-\u0DFF]/g) ?? []).length;
  if (letters / text.length < 0.5) {
    return {
      ok: false,
      reason:
        "This does not look like readable study material. Please paste relevant text instead of symbols, numbers or random characters.",
    };
  }

  const words = text
    .toLowerCase()
    .replace(/[^a-z\u0900-\u0dff\s]/g, " ")
    .split(/\s+/)
    .filter(Boolean);

  if (words.length < 25) {
    return {
      ok: false,
      reason:
        "Not enough words to work with. Please paste relevant study material of at least a short paragraph.",
    };
  }

  const unique = new Set(words);
  const uniqueRatio = unique.size / words.length;

  // "hello hello hello ..." → almost no unique words.
  if (uniqueRatio < 0.25) {
    return {
      ok: false,
      reason:
        "The text is highly repetitive — the same words repeat over and over. Please provide relevant study material.",
    };
  }

  // One token dominating the whole paste.
  const counts = new Map<string, number>();
  words.forEach((w) => counts.set(w, (counts.get(w) ?? 0) + 1));
  const topShare = Math.max(...counts.values()) / words.length;
  if (topShare > 0.35) {
    return {
      ok: false,
      reason:
        "One word is repeated through most of the text. Please provide relevant study material instead of repeated words.",
    };
  }

  // Meaningful content words, not just stop-words or gibberish tokens.
  const content = [...unique].filter((w) => w.length > 3 && !STOP.has(w));
  if (content.length < 8) {
    return {
      ok: false,
      reason:
        "No meaningful subject terms were found. Please paste relevant syllabus, notes or chapter text.",
    };
  }

  // Vowel-less gibberish like "asdf qwer zxcv".
  const gibberish = content.filter((w) => !/[aeiou\u0900-\u0dff]/.test(w)).length;
  if (gibberish / content.length > 0.4) {
    return {
      ok: false,
      reason:
        "The text looks like random characters rather than language. Please provide relevant study material.",
    };
  }

  // Needs some sentence structure to draw questions from.
  const sentences = text.split(/[.!?\u0964]+/).filter((s) => s.trim().split(/\s+/).length >= 5);
  if (sentences.length < 2) {
    return {
      ok: false,
      reason:
        "The text has no proper sentences to build questions from. Please paste relevant study material written in full sentences.",
    };
  }

  return { ok: true };
}
