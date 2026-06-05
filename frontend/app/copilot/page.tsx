import { api } from "@/lib/api";
import ModuleHeader from "@/components/ModuleHeader";
import CopilotChat from "@/components/CopilotChat";

export const dynamic = "force-dynamic";

export default async function CopilotPage() {
  const s = await api.copilotSuggested();
  const engine = s?.engine;
  const ready = engine?.available;

  return (
    <div>
      <ModuleHeader title="AI Research Copilot" subtitle={`Module 12 · grounded on live terminal data · ${engine?.model ?? "AI engine"}`} />
      <div className="p-5">
        {!ready && (
          <div className="mb-4 rounded-xl border border-terminal-warn/30 bg-terminal-warn/5 px-4 py-3 text-xs text-terminal-muted">
            <span className="text-terminal-warn font-semibold">AI engine not configured.</span>{" "}
            Set a free <code className="text-terminal-accent">GROQ_API_KEY</code> (from console.groq.com) in the
            backend environment to enable the copilot. You can still type — it will retry.
          </div>
        )}
        <CopilotChat suggested={s?.suggested ?? []} engine={engine?.model} />
      </div>
    </div>
  );
}
