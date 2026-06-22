"use client";

import Link from "next/link";
import { usePathname } from "next/navigation";
import {
  Activity, Binoculars, Bot, BookOpen, BrainCircuit, CloudRain, Coins, FlaskConical,
  Gauge, GitCompareArrows, LineChart, Newspaper, Satellite, Sigma, TrendingUp,
} from "lucide-react";
import { cn } from "@/lib/utils";
import ThemeToggle from "@/components/ThemeToggle";

const WEATHER = [
  { label: "Weather Command", icon: CloudRain, href: "/" },
  { label: "Derivative Monitor", icon: LineChart, href: "/derivative" },
  { label: "Monsoon Intel", icon: Gauge, href: "/monsoon" },
  { label: "Satellite Intel", icon: Satellite, href: "/satellite" },
  { label: "Research Lab", icon: FlaskConical, href: "/research" },
  { label: "ML Lab", icon: BrainCircuit, href: "/ml" },
  { label: "Revision Engine", icon: GitCompareArrows, href: "/revision" },
  { label: "Probability Engine", icon: Sigma, href: "/probability" },
  { label: "Trading Signal", icon: TrendingUp, href: "/signal" },
  { label: "Scenario Analysis", icon: Binoculars, href: "/scenarios" },
  { label: "Alt-Data Research", icon: Newspaper, href: "/altdata" },
  { label: "AI Copilot", icon: Bot, href: "/copilot" },
  { label: "Guide & Glossary", icon: BookOpen, href: "/guide" },
];

function NavItem({ item, active }: { item: { label: string; icon: typeof Coins; href: string }; active: boolean }) {
  return (
    <Link
      href={item.href}
      className={cn(
        "flex items-center gap-3 px-4 py-2 text-sm",
        active
          ? "bg-terminal-card text-terminal-text border-l-2 border-terminal-accent"
          : "text-terminal-muted hover:text-terminal-text/90 hover:bg-terminal-card/40",
      )}
    >
      <item.icon className="h-4 w-4 shrink-0" />
      <span className="flex-1 truncate">{item.label}</span>
    </Link>
  );
}

function SectionLabel({ children }: { children: React.ReactNode }) {
  return <div className="px-4 pt-3 pb-1 text-[9px] uppercase tracking-widest text-terminal-muted/70">{children}</div>;
}

export default function Sidebar() {
  const pathname = usePathname();
  return (
    <aside className="w-60 shrink-0 border-r border-terminal-border bg-terminal-panel flex flex-col">
      <div className="px-4 h-14 flex items-center gap-2 border-b border-terminal-border">
        <Activity className="h-5 w-5 text-terminal-accent" />
        <div className="leading-tight">
          <div className="text-sm font-bold text-terminal-text">RAINMUMBAI TERMINAL</div>
          <div className="text-[10px] uppercase tracking-widest text-terminal-muted">Weather Derivatives</div>
        </div>
      </div>

      <nav className="flex-1 overflow-y-auto py-1">
        <SectionLabel>Weather · RAINMUMBAI</SectionLabel>
        <div className="px-4 pb-1.5 leading-tight">
          <div className="text-[9px] text-terminal-muted">Santacruz · 19.0896°N, 72.8656°E</div>
        </div>
        {WEATHER.map((m) => (
          <NavItem key={m.href} item={m} active={m.href === pathname || (m.href === "/" && pathname === "/")} />
        ))}
      </nav>

      <div className="px-4 py-3 border-t border-terminal-border flex items-center justify-between gap-2">
        <span className="text-[10px] text-terminal-muted">NCDEX · RAINMUMBAI</span>
        <ThemeToggle />
      </div>
    </aside>
  );
}
