import type { Metadata } from "next";
import "./globals.css";
import Sidebar from "@/components/Sidebar";
import AutoRefresh from "@/components/AutoRefresh";

export const metadata: Metadata = {
  title: "RAINMUMBAI Terminal",
  description: "Weather derivatives research & trading terminal — NCDEX RAINMUMBAI",
};

const THEME_INIT = `(function(){try{var t=localStorage.getItem('theme')||'dark';document.documentElement.classList.add(t);}catch(e){document.documentElement.classList.add('dark');}})();`;

export default function RootLayout({ children }: { children: React.ReactNode }) {
  return (
    <html lang="en" suppressHydrationWarning>
      <head>
        <script dangerouslySetInnerHTML={{ __html: THEME_INIT }} />
      </head>
      <body className="font-mono antialiased">
        <AutoRefresh seconds={180} />
        <div className="flex h-screen overflow-hidden">
          <Sidebar />
          <main className="flex-1 overflow-y-auto">{children}</main>
        </div>
      </body>
    </html>
  );
}
