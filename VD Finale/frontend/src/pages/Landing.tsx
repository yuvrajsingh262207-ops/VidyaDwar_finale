import { ArrowRight, Check, CircleHelp, FileCheck2, GitBranch, GraduationCap, Landmark, ShieldCheck, Sparkles } from "lucide-react";
import { Link, useNavigate } from "react-router-dom";
import { Brand } from "@/components/Brand";
import { Button } from "@/components/ui/button";

const journey = ["PROFILE", "MATCH", "UNDERSTAND", "DOCUMENTS", "COMPARE", "CONFLICT CHECK", "EVIDENCE", "DECIDE", "APPLY"];
const capabilities = [
  [GraduationCap, "Personalized matching", "See relevant records through the lens of your course, marks, income, and state."],
  [CircleHelp, "Explainable eligibility", "Every result shows the rule, your value, and a plain-language reason."],
  [FileCheck2, "Document readiness", "Know what supports each condition before you leave for the official portal."],
  [GitBranch, "Stage-aware conflict graph", "The core innovation: understand where two awards may interact across their lifecycle."],
  [ShieldCheck, "Evidence-locked explanations", "Warnings stay connected to a stored rule, source, clause, and date checked."],
  [Landmark, "Official next steps", "Vidyadwar helps you prepare; the official authority remains the final decision-maker."],
];

export default function Landing() {
  const navigate = useNavigate();
  return (
    <div className="min-h-svh overflow-hidden bg-[#fafafc] text-slate-900">
      <header className="relative z-10 border-b border-slate-200/80 bg-white/85 backdrop-blur-xl">
        <div className="mx-auto flex max-w-7xl items-center justify-between px-5 py-4 lg:px-8">
          <Brand />
          <nav className="hidden items-center gap-7 text-sm font-semibold text-slate-600 md:flex" aria-label="Public navigation">
            <Link data-testid="landing-how-it-works-link" to="/how-it-works" className="transition-colors hover:text-teal-700">How it works</Link>
            <Link data-testid="landing-scholarships-link" to="/scholarships" className="transition-colors hover:text-teal-700">Explore scholarships</Link>
            <Link data-testid="landing-login-link" to="/login" className="transition-colors hover:text-teal-700">Sign in</Link>
          </nav>
          <Button data-testid="landing-get-started-button" onClick={() => navigate("/login")} className="bg-slate-950 px-5 text-white hover:bg-teal-700">Get started <ArrowRight /></Button>
        </div>
      </header>

      <main>
        <section className="relative mx-auto grid max-w-7xl items-center gap-14 px-5 pb-20 pt-16 lg:grid-cols-[1.05fr_.95fr] lg:px-8 lg:pb-28 lg:pt-24">
          <div className="absolute -left-32 top-6 h-72 w-72 rounded-full bg-teal-200/30 blur-3xl" />
          <div className="relative">
            <div className="mb-7 inline-flex items-center gap-2 rounded-full border border-teal-200 bg-teal-50 px-3 py-1.5 text-xs font-bold uppercase tracking-[0.16em] text-teal-800"><Sparkles className="size-3.5" /> CODEX 2026 · AlgoRush</div>
            <h1 data-testid="landing-hero-heading" className="max-w-3xl font-heading text-5xl font-extrabold leading-[.98] tracking-[-0.05em] text-slate-950 sm:text-6xl lg:text-7xl">Find. Understand.<br /><span className="text-teal-700">Check. Decide. Apply.</span></h1>
            <p data-testid="landing-hero-description" className="mt-7 max-w-xl text-lg leading-8 text-slate-600">Understand scholarship eligibility, documents, and possible scholarship conflicts before making an application decision.</p>
            <p className="mt-4 max-w-xl text-sm leading-6 text-slate-500">Vidyadwar is a decision-support layer around scholarship information — not a replacement for official scholarship authorities.</p>
            <div className="mt-9 flex flex-wrap gap-3">
              <Button data-testid="landing-primary-cta" onClick={() => navigate("/login")} className="h-11 bg-teal-700 px-6 text-white hover:bg-teal-800">Get started <ArrowRight /></Button>
              <Button data-testid="landing-explore-cta" variant="outline" onClick={() => navigate("/scholarships")} className="h-11 border-slate-300 bg-white px-6">Explore scholarships</Button>
              <Link data-testid="landing-how-it-works-cta" to="/how-it-works" className="inline-flex h-11 items-center gap-2 px-3 text-sm font-bold text-slate-700 transition-colors hover:text-teal-700">How it works <ArrowRight className="size-4" /></Link>
            </div>
            <div className="mt-12 flex flex-wrap gap-x-7 gap-y-3 text-xs font-semibold text-slate-500"><span className="flex items-center gap-2"><Check className="size-4 text-teal-600" /> Rule-based decisions</span><span className="flex items-center gap-2"><Check className="size-4 text-teal-600" /> Evidence before advice</span><span className="flex items-center gap-2"><Check className="size-4 text-teal-600" /> Official portal handoff</span></div>
          </div>
          <div className="relative min-h-[430px] rounded-[2rem] bg-slate-950 p-5 shadow-2xl shadow-slate-300/50 sm:p-7">
            <div className="absolute right-10 top-0 h-36 w-36 rounded-full bg-teal-500/30 blur-3xl" />
            <div className="relative flex items-center justify-between border-b border-white/10 pb-5"><div><p className="font-mono text-[10px] uppercase tracking-[.2em] text-teal-300">Decision command center</p><p className="mt-2 text-xl font-bold text-white">A clearer path to support</p></div><div className="rounded-full border border-amber-400/40 bg-amber-400/10 px-3 py-1 text-[10px] font-bold uppercase tracking-wider text-amber-300">Demo ready</div></div>
            <div className="relative mt-8 grid grid-cols-2 gap-3 sm:gap-4">
              <div className="col-span-2 rounded-2xl border border-teal-400/30 bg-teal-400/10 p-5"><div className="flex items-center justify-between"><span className="text-xs font-bold uppercase tracking-[.15em] text-teal-200">Student profile</span><span className="size-2 rounded-full bg-teal-300" /></div><div className="mt-4 flex items-end justify-between"><div><p className="text-2xl font-extrabold text-white">Aarav</p><p className="mt-1 text-sm text-slate-300">B.Tech · 82% · Maharashtra</p></div><div className="text-right"><p className="font-mono text-2xl font-bold text-teal-300">4/5</p><p className="text-[10px] uppercase tracking-wider text-slate-400">docs ready</p></div></div></div>
              <div className="rounded-2xl border border-white/10 bg-white/5 p-4"><p className="text-xs font-bold uppercase tracking-wider text-slate-400">Matches</p><p className="mt-3 text-3xl font-extrabold text-white">4</p><p className="mt-1 text-xs text-teal-200">profile-fit records</p></div>
              <div className="rounded-2xl border border-amber-300/20 bg-amber-300/10 p-4"><p className="text-xs font-bold uppercase tracking-wider text-amber-200">Conflict check</p><p className="mt-3 text-3xl font-extrabold text-white">1</p><p className="mt-1 text-xs text-amber-200">stage to verify</p></div>
              <div className="col-span-2 flex items-center justify-between rounded-2xl border border-white/10 bg-white/5 p-4"><div><p className="text-xs font-bold uppercase tracking-wider text-slate-400">Evidence locked</p><p className="mt-2 text-sm font-semibold text-white">Receiving / Disbursement</p></div><div className="flex items-center gap-1 text-xs font-bold text-amber-300"><ShieldCheck className="size-4" /> Demo Rule</div></div>
            </div>
          </div>
        </section>

        <section className="border-y border-slate-200 bg-white py-8"><div className="mx-auto flex max-w-7xl flex-wrap items-center justify-center gap-2 px-5 lg:px-8">{journey.map((item, index) => <div key={item} className="flex items-center gap-2"><span data-testid={`journey-step-${index + 1}`} className={`rounded-full px-3 py-2 font-mono text-[10px] font-bold tracking-wider ${item === "CONFLICT CHECK" ? "bg-slate-950 text-teal-200" : "bg-slate-100 text-slate-600"}`}>{item}</span>{index < journey.length - 1 && <ArrowRight className="size-3 text-slate-300" />}</div>)}</div></section>

        <section className="mx-auto max-w-7xl px-5 py-20 lg:px-8 lg:py-28"><div className="max-w-2xl"><p className="font-mono text-xs font-bold uppercase tracking-[.2em] text-teal-700">Why Vidyadwar?</p><h2 className="mt-4 font-heading text-4xl font-extrabold tracking-tight text-slate-950">The decision layer between “found it” and “ready to apply.”</h2><p className="mt-5 text-base leading-7 text-slate-600">Students need more than a list. They need to know why a record matches, what evidence supports the rule, and at which point two benefits may interact.</p></div><div className="mt-12 grid gap-4 md:grid-cols-2 lg:grid-cols-3">{capabilities.map(([Icon, title, copy], index) => <div key={title as string} data-testid={`capability-card-${index + 1}`} className={`rounded-2xl border p-6 transition-transform duration-200 hover:-translate-y-1 ${index === 3 ? "border-teal-300 bg-teal-50/70" : "border-slate-200 bg-white"}`}><Icon className={`size-6 ${index === 3 ? "text-teal-700" : "text-slate-800"}`} /><h3 className="mt-5 font-heading text-lg font-bold text-slate-950">{title as string}</h3><p className="mt-2 text-sm leading-6 text-slate-600">{copy as string}</p></div>)}</div></section>

        <section className="bg-slate-950 px-5 py-16 text-white lg:px-8"><div className="mx-auto flex max-w-7xl flex-col items-start justify-between gap-8 md:flex-row md:items-center"><div><p className="font-mono text-xs uppercase tracking-[.2em] text-teal-300">Start with a fictional student</p><h2 className="mt-3 font-heading text-3xl font-extrabold tracking-tight">Take Aarav from profile to official portal.</h2><p className="mt-3 max-w-xl text-sm leading-6 text-slate-300">One click loads a realistic demo profile and the complete decision journey. Every prototype rule stays visibly labeled.</p></div><Button data-testid="landing-demo-mode-button" onClick={() => navigate("/login")} className="h-12 bg-teal-500 px-6 font-bold text-slate-950 hover:bg-teal-300">Launch Demo Mode <ArrowRight /></Button></div></section>
      </main>
      <footer className="bg-slate-950 px-5 pb-8 text-slate-400 lg:px-8"><div className="mx-auto flex max-w-7xl flex-col gap-5 border-t border-white/10 pt-7 text-xs md:flex-row md:items-center md:justify-between"><div className="flex items-center gap-3"><Brand compact light /><span>AI-Powered Scholarship Decision Navigator</span></div><p>Final eligibility and disbursement remain with the respective official authority.</p><div className="flex gap-4"><Link data-testid="footer-how-it-works-link" to="/how-it-works">How it works</Link><Link data-testid="footer-privacy-link" to="/privacy">Privacy</Link><Link data-testid="footer-terms-link" to="/terms">Terms</Link></div></div></footer>
    </div>
  );
}