export default function ModuleHeader({ title, subtitle }: { title: string; subtitle?: string }) {
  return (
    <div className="h-14 px-5 flex items-center justify-between border-b border-terminal-border bg-terminal-panel">
      <div>
        <h1 className="text-base font-semibold text-terminal-text">{title}</h1>
        {subtitle && <p className="text-[11px] text-terminal-muted">{subtitle}</p>}
      </div>
    </div>
  );
}
