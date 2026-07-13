import { Link } from "@tanstack/react-router";
import { Brain, FileText, BarChart3, Sparkles } from "lucide-react";

export function Header() {
  return (
    <header className="sticky top-0 z-40 border-b border-primary/20 bg-primary/90 backdrop-blur-xl shadow-glow">
      <div className="mx-auto flex h-16 max-w-7xl items-center justify-between px-6">
        <Link to="/" className="flex items-center gap-2">
          <div className="grid h-9 w-9 place-items-center rounded-lg bg-white/15 shadow-glow">
            <Brain className="h-5 w-5 text-white" />
          </div>
          <div className="leading-tight">
            <div className="font-display text-base font-semibold text-white">QGen<span className="text-white/80">.AI</span></div>
            <div className="text-[10px] uppercase tracking-widest text-white/60">NLP Question Paper</div>
          </div>
        </Link>
        <nav className="hidden items-center gap-1 md:flex">
          <NavLink to="/" icon={<Sparkles className="h-4 w-4" />}>Home</NavLink>
          <NavLink to="/generate" icon={<FileText className="h-4 w-4" />}>Generate</NavLink>
          <NavLink to="/papers" icon={<FileText className="h-4 w-4" />}>Papers</NavLink>
          <NavLink to="/analytics" icon={<BarChart3 className="h-4 w-4" />}>Analytics</NavLink>
        </nav>
      </div>
    </header>
  );
}

function NavLink({ to, children, icon }: { to: string; children: React.ReactNode; icon: React.ReactNode }) {
  return (
    <Link
      to={to}
      className="flex items-center gap-2 rounded-md px-3 py-2 text-sm font-medium text-white/70 transition-colors hover:bg-white/10 hover:text-white"
      activeProps={{ className: "bg-white/15 text-white" }}
      activeOptions={{ exact: to === "/" }}
    >
      {icon}
      {children}
    </Link>
  );
}
