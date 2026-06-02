import { Link } from "@tanstack/react-router";
import { Brain, FileText, BarChart3, Sparkles, Settings } from "lucide-react";
import { useState } from "react";
import { Dialog, DialogContent, DialogHeader, DialogTitle, DialogTrigger } from "@/components/ui/dialog";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import { getBackendUrl, setBackendUrl } from "@/lib/api";
import { toast } from "sonner";

export function Header() {
  const [open, setOpen] = useState(false);
  const [url, setUrl] = useState(typeof window !== "undefined" ? getBackendUrl() : "");

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
        <Dialog open={open} onOpenChange={setOpen}>
          <DialogTrigger asChild>
            <Button variant="outline" size="sm" className="gap-2 border-white/30 bg-white/10 text-white hover:bg-white/20 hover:text-white">
              <Settings className="h-4 w-4" /> Backend
            </Button>
          </DialogTrigger>
          <DialogContent>
            <DialogHeader><DialogTitle>FastAPI backend URL</DialogTitle></DialogHeader>
            <div className="space-y-3">
              <p className="text-sm text-muted-foreground">
                Point this UI to your running FastAPI server (e.g.{" "}
                <code className="rounded bg-muted px-1">http://localhost:8000</code>).
                Leave empty to use the built-in demo generator.
              </p>
              <Label>Base URL</Label>
              <Input value={url} onChange={(e) => setUrl(e.target.value)} placeholder="http://localhost:8000" />
              <p className="text-xs text-muted-foreground">
                Expected endpoint: <code>POST /generate</code> with JSON{" "}
                <code>{`{ text, config, title }`}</code> returning the paper object.
              </p>
              <Button
                className="w-full bg-gradient-primary text-primary-foreground"
                onClick={() => {
                  setBackendUrl(url);
                  toast.success(url ? "Backend connected" : "Using demo generator");
                  setOpen(false);
                }}
              >
                Save
              </Button>
            </div>
          </DialogContent>
        </Dialog>
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
