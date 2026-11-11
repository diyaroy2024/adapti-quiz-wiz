// Browser-side text extraction from PDF + DOCX.
import mammoth from "mammoth";

export interface ExtractedDocument {
  text: string;
  pages?: { page: number; text: string }[];
}

export async function extractText(file: File): Promise<string> {
  return (await extractDocument(file)).text;
}

export async function extractDocument(file: File): Promise<ExtractedDocument> {
  const name = file.name.toLowerCase();
  if (name.endsWith(".txt") || file.type.startsWith("text/")) {
    return { text: await file.text() };
  }
  if (name.endsWith(".docx")) {
    const buf = await file.arrayBuffer();
    const { value } = await mammoth.extractRawText({ arrayBuffer: buf });
    return { text: value };
  }
  if (name.endsWith(".pdf")) {
    return extractPdf(file);
  }
  throw new Error("Unsupported file. Use .txt, .pdf, or .docx");
}

async function extractPdf(file: File): Promise<ExtractedDocument> {
  const pdfjs: any = await import("pdfjs-dist/build/pdf.mjs");
  const workerUrl = (await import("pdfjs-dist/build/pdf.worker.mjs?url")).default;
  pdfjs.GlobalWorkerOptions.workerSrc = workerUrl;
  const buf = await file.arrayBuffer();
  const pdf = await pdfjs.getDocument({ data: buf }).promise;
  const pages: { page: number; text: string }[] = [];
  for (let i = 1; i <= pdf.numPages; i++) {
    const page = await pdf.getPage(i);
    const content = await page.getTextContent();
    pages.push({ page: i, text: content.items.map((it: any) => it.str).join(" ").trim() });
  }
  return { text: pages.map((page) => page.text).join("\n\n"), pages };
}
