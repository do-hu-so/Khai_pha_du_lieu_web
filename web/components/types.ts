import type { RagTrace, SourceRef } from "@/lib/rag/types";

export interface UIMessage {
  id: string;
  role: "user" | "assistant";
  content: string;
  sources?: SourceRef[];
  trace?: RagTrace;
  error?: string;
  pending?: boolean;
}

export interface HealthInfo {
  ok: boolean;
  error?: string;
  index?: {
    numChunks: number;
    numDocs: number;
    model: string;
    createdAt: string;
    bySource: Record<string, number>;
    sources: Record<string, string>;
  };
  config?: { groqConfigured: boolean; model: string; reranker: string };
}
