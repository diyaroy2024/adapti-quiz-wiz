import { createFileRoute, useNavigate, Link } from "@tanstack/react-router";
import { useEffect, useState } from "react";
import { toast } from "sonner";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import { Tabs, TabsContent, TabsList, TabsTrigger } from "@/components/ui/tabs";
import { GraduationCap, Loader2, ShieldCheck } from "lucide-react";
import { useAuth } from "@/lib/auth";

export const Route = createFileRoute("/auth")({
  head: () => ({
    meta: [
      { title: "Sign in — QGen.AI Question Paper Generator" },
      {
        name: "description",
        content:
          "Sign in or create a teacher account to save your generated question papers, source documents and analytics.",
      },
      { property: "og:title", content: "Sign in — QGen.AI" },
      {
        property: "og:description",
        content: "Create a teacher account to keep your question papers and analytics private to you.",
      },
      { property: "og:type", content: "website" },
      { name: "twitter:card", content: "summary_large_image" },
    ],
  }),
  component: AuthPage,
});

function AuthPage() {
  const { user, signIn, signUp, backendConfigured } = useAuth();
  const navigate = useNavigate();
  const [busy, setBusy] = useState(false);

  const [name, setName] = useState("");
  const [email, setEmail] = useState("");
  const [password, setPassword] = useState("");

  useEffect(() => {
    if (user) navigate({ to: "/generate", replace: true });
  }, [user, navigate]);

  async function submit(mode: "in" | "up") {
    if (!email.trim() || password.length < 8) {
      toast.error("Enter your email and a password of at least 8 characters");
      return;
    }
    if (mode === "up" && !name.trim()) {
      toast.error("Enter your name");
      return;
    }
    setBusy(true);
    try {
      if (mode === "in") await signIn(email.trim(), password);
      else await signUp(name.trim(), email.trim(), password);
      toast.success("Signed in");
      navigate({ to: "/generate", replace: true });
    } catch (e: any) {
      toast.error(e.message ?? "Could not sign you in");
    } finally {
      setBusy(false);
    }
  }

  return (
    <div className="mx-auto flex max-w-md flex-col px-6 py-14">
      <div className="mb-8 text-center">
        <div className="mx-auto mb-4 grid h-14 w-14 place-items-center rounded-2xl bg-primary/15 text-primary">
          <GraduationCap className="h-7 w-7" />
        </div>
        <h1 className="font-display text-3xl font-semibold">Teacher account</h1>
        <p className="mt-2 text-sm text-muted-foreground">
          Your papers, source documents and analytics stay private to your account.
        </p>
      </div>


      <div className="rounded-2xl bg-gradient-card p-6 shadow-card">
        <Tabs defaultValue="in">
          <TabsList className="mb-5 grid w-full grid-cols-2">
            <TabsTrigger value="in">Sign in</TabsTrigger>
            <TabsTrigger value="up">Create account</TabsTrigger>
          </TabsList>

          <TabsContent value="in" className="space-y-4">
            <Field id="email-in" label="Email" type="email" value={email} onChange={setEmail} />
            <Field id="pw-in" label="Password" type="password" value={password} onChange={setPassword} />
            <Button className="w-full gap-2 bg-gradient-primary text-primary-foreground" disabled={busy} onClick={() => submit("in")}>
              {busy ? <Loader2 className="h-4 w-4 animate-spin" /> : <ShieldCheck className="h-4 w-4" />}
              Sign in
            </Button>
          </TabsContent>

          <TabsContent value="up" className="space-y-4">
            <Field id="name-up" label="Full name" value={name} onChange={setName} />
            <Field id="email-up" label="Email" type="email" value={email} onChange={setEmail} />
            <Field id="pw-up" label="Password" type="password" value={password} onChange={setPassword} hint="At least 8 characters" />
            <Button className="w-full gap-2 bg-gradient-primary text-primary-foreground" disabled={busy} onClick={() => submit("up")}>
              {busy ? <Loader2 className="h-4 w-4 animate-spin" /> : <ShieldCheck className="h-4 w-4" />}
              Create account
            </Button>
          </TabsContent>
        </Tabs>
      </div>

      <p className="mt-6 text-center text-xs text-muted-foreground">
        <Link to="/" className="underline">Back to home</Link>
      </p>
    </div>
  );
}

function Field({
  id,
  label,
  value,
  onChange,
  type = "text",
  hint,
}: {
  id: string;
  label: string;
  value: string;
  onChange: (v: string) => void;
  type?: string;
  hint?: string;
}) {
  return (
    <div className="space-y-1.5">
      <Label htmlFor={id}>{label}</Label>
      <Input id={id} type={type} value={value} onChange={(e) => onChange(e.target.value)} />
      {hint && <p className="text-xs text-muted-foreground">{hint}</p>}
    </div>
  );
}
