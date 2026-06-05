"use client";

import { useRef, useState } from "react";
import { Send, Bot, User, Loader2 } from "lucide-react";
import { cn } from "@/lib/utils";

interface Msg { role: "user" | "assistant"; text: string; }

export default function CopilotChat({ suggested, engine }: { suggested: string[]; engine?: string }) {
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
      const res = await fetch("/api/copilot", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ question }),
      });
      const data = await res.json();
      setMessages((m) => [...m, { role: "assistant", text: data.answer ?? "No answer." }]);
    } catch {
      setMessages((m) => [...m, { role: "assistant", text: "Request failed — the AI engine may be unavailable." }]);
    } finally {
      setLoading(false);
      setTimeout(() => scrollRef.current?.scrollTo({ top: scrollRef.current.scrollHeight }), 50);
    }
  }

  return (
    <div className="flex flex-col h-[calc(100vh-180px)]">
      <div ref={scrollRef} className="flex-1 overflow-y-auto space-y-4 pr-1">
        {messages.length === 0 && (
          <div className="text-terminal-muted text-sm">
            <p className="mb-3">Ask about today&apos;s forecast, signal, drivers, or risks. Answers are grounded
              on the terminal&apos;s live data{engine ? ` · ${engine}` : ""}.</p>
            <div className="flex flex-wrap gap-2">
              {suggested.map((s) => (
                <button key={s} onClick={() => ask(s)}
                  className="text-xs rounded-full border border-terminal-border px-3 py-1.5 text-terminal-text hover:border-terminal-accent/60 hover:text-terminal-accent transition-colors">
                  {s}
                </button>
              ))}
            </div>
          </div>
        )}
        {messages.map((m, i) => (
          <div key={i} className={cn("flex gap-3", m.role === "user" ? "justify-end" : "justify-start")}>
            {m.role === "assistant" && <Bot className="h-5 w-5 text-terminal-accent shrink-0 mt-1" />}
            <div className={cn("max-w-[80%] rounded-xl px-4 py-2.5 text-sm whitespace-pre-wrap leading-relaxed",
              m.role === "user" ? "bg-terminal-accent/15 text-terminal-text" : "bg-terminal-card border border-terminal-border text-terminal-text")}>
              {m.text}
            </div>
            {m.role === "user" && <User className="h-5 w-5 text-terminal-muted shrink-0 mt-1" />}
          </div>
        ))}
        {loading && (
          <div className="flex gap-3">
            <Bot className="h-5 w-5 text-terminal-accent shrink-0 mt-1" />
            <div className="rounded-xl px-4 py-2.5 bg-terminal-card border border-terminal-border text-terminal-muted text-sm flex items-center gap-2">
              <Loader2 className="h-4 w-4 animate-spin" /> Thinking…
            </div>
          </div>
        )}
      </div>

      <form onSubmit={(e) => { e.preventDefault(); ask(input); }} className="mt-3 flex gap-2">
        <input
          value={input}
          onChange={(e) => setInput(e.target.value)}
          placeholder="Ask the research copilot…"
          className="flex-1 rounded-lg border border-terminal-border bg-terminal-panel px-3 py-2 text-sm text-terminal-text placeholder:text-terminal-muted focus:outline-none focus:border-terminal-accent/60"
        />
        <button type="submit" disabled={loading || !input.trim()}
          className="rounded-lg bg-terminal-accent/20 border border-terminal-accent/40 px-3 text-terminal-accent disabled:opacity-40">
          <Send className="h-4 w-4" />
        </button>
      </form>
    </div>
  );
}
