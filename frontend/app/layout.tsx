import type { Metadata } from "next";
import Link from "next/link";
import "./globals.css";

export const metadata: Metadata = {
  title: "PromptBench Studio",
  description: "Benchmarking de prompts: versionamento, custo, regressão por slice.",
};

export default function RootLayout({
  children,
}: {
  children: React.ReactNode;
}) {
  return (
    <html lang="pt-BR" className="dark">
      <body className="min-h-screen bg-slate-950 text-slate-200 font-sans antialiased">
        <header className="border-b border-slate-800 bg-slate-950/80 backdrop-blur sticky top-0 z-10">
          <div className="mx-auto max-w-7xl px-4 h-14 flex items-center justify-between">
            <Link
              href="/"
              className="text-sm font-semibold tracking-tight text-slate-100"
            >
              PromptBench <span className="text-slate-500">Studio</span>
            </Link>
            <nav className="text-xs flex gap-4 text-slate-400">
              <Link href="/" className="hover:text-slate-200">tasks</Link>
              <Link href="/compare" className="hover:text-slate-200">compare</Link>
            </nav>
          </div>
        </header>
        <main className="mx-auto max-w-7xl px-4 py-6">{children}</main>
      </body>
    </html>
  );
}
