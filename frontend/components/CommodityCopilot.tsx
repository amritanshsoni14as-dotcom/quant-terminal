"use client";

import { useRef, useState } from "react";
import { Send, Bot, User, Loader2 } from "lucide-react";
import { cn } from "@/lib/utils";

interface Msg { role: "user" | "assistant"; text: string; }

export default function CommodityCopilot({ symbol, suggested }: { symbol: string; suggested: string[] }) {
  const [messages, setMessages] = useState<Msg[]>([]);
  const [input, setInput] = useState("");
  const [loading, setLoading] = useState(false);
  const scrollRef = useRef<HTMLDivElement>(null);

  async function ask(q: string) {
    const question = q.trim();
    if (!question || loading) return;
    setInput("");
    setMessages((m) => [...m, { role: "user", text: question }]);
    setLoading(true);
    try {
      const res = await fetch("/api/commodity-copilot", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ symbol, question }),
      });
      const data = await res.json();
      setMessages((m) => [...m, { role: "assistant", text: data.answer ?? "No answer." }]);
    } catch {
      setMessages((m) => [...m, { role: "assistant", text: "Request failed — is the local model running?" }]);
    } finally {
      setLoading(false);
      setTimeout(() => scrollRef.current?.scrollTo({ top: scrollRef.current.scrollHeight }), 50);
    }
  }

  return (
    <div>
      <div ref={scrollRef} className="max-h-[360px] overflow-y-auto space-y-3 mb-3">
        {messages.length === 0 && (
          <div className="flex flex-wrap gap-2">
            {suggested.map((s) => (
              <button key={s} onClick={() => ask(s)}
                className="text-xs rounded-full border border-terminal-border px-3 py-1.5 text-terminal-text hover:border-terminal-accent/60 hover:text-terminal-accent transition-colors">
                {s}
              </button>
            ))}
          </div>
        )}
        {messages.map((m, i) => (
          <div key={i} className={cn("flex gap-2.5", m.role === "user" ? "justify-end" : "justify-start")}>
            {m.role === "assistant" && <Bot className="h-4 w-4 text-terminal-accent shrink-0 mt-1" />}
            <div className={cn("max-w-[85%] rounded-xl px-3 py-2 text-sm whitespace-pre-wrap leading-relaxed",
              m.role === "user" ? "bg-terminal-accent/15 text-terminal-text" : "bg-terminal-panel border border-terminal-border text-terminal-text")}>
              {m.text}
            </div>
            {m.role === "user" && <User className="h-4 w-4 text-terminal-muted shrink-0 mt-1" />}
          </div>
        ))}
        {loading && (
          <div className="flex gap-2.5">
            <Bot className="h-4 w-4 text-terminal-accent shrink-0 mt-1" />
            <div className="rounded-xl px-3 py-2 bg-terminal-panel border border-terminal-border text-terminal-muted text-sm flex items-center gap-2">
              <Loader2 className="h-4 w-4 animate-spin" /> Thinking… (local CPU model — ~1–2 minutes)
            </div>
          </div>
        )}
      </div>
      <form onSubmit={(e) => { e.preventDefault(); ask(input); }} className="flex gap-2">
        <input value={input} onChange={(e) => setInput(e.target.value)}
          placeholder={`Ask about ${symbol}…`}
          className="flex-1 rounded-lg border border-terminal-border bg-terminal-panel px-3 py-2 text-sm text-terminal-text placeholder:text-terminal-muted focus:outline-none focus:border-terminal-accent/60" />
        <button type="submit" disabled={loading || !input.trim()}
          className="rounded-lg bg-terminal-accent/20 border border-terminal-accent/40 px-3 text-terminal-accent disabled:opacity-40">
          <Send className="h-4 w-4" />
        </button>
      </form>
    </div>
  );
}
