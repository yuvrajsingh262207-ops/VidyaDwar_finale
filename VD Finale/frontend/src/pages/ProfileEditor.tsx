import { useState } from "react";
import type { FormEvent, ReactNode } from "react";
import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { Check, CircleAlert, GraduationCap, ShieldCheck, UserRound } from "lucide-react";
import { toast } from "sonner";
import { Workspace } from "@/pages/Workspace";
import { ApiError, apiGet, apiPut } from "@/lib/api";
import type { AuthResponse, Profile, ProfileUpdate } from "@/lib/types";
import { Button } from "@/components/ui/button";

export default function ProfileEditor() {
  const queryClient = useQueryClient();
  const profileQuery = useQuery({ queryKey: ["profile"], queryFn: () => apiGet<Profile>("/profile"), retry: false });
  const sessionQuery = useQuery({ queryKey: ["auth-session"], queryFn: () => apiGet<AuthResponse>("/auth/me"), retry: false });
  const [draft, setDraft] = useState<Profile | null>(null);
  const [success, setSuccess] = useState("");
  const [failure, setFailure] = useState("");

  const save = useMutation({
    mutationFn: (profile: Profile) => {
      const { user_id: _userId, ...payload } = profile;
      return apiPut<Profile>("/profile", payload satisfies ProfileUpdate);
    },
    onSuccess: async (saved) => {
      setDraft(saved);
      setFailure("");
      setSuccess("Profile saved successfully.");
      queryClient.setQueryData(["profile"], saved);
      await Promise.all([
        queryClient.invalidateQueries({ queryKey: ["auth-session"] }),
        queryClient.invalidateQueries({ queryKey: ["dashboard"] }),
        queryClient.invalidateQueries({ queryKey: ["scholarships"] }),
        queryClient.invalidateQueries({ queryKey: ["scholarship"] }),
        queryClient.invalidateQueries({ queryKey: ["conflict"] }),
        queryClient.invalidateQueries({ queryKey: ["readiness"] }),
      ]);
      toast.success("Profile saved successfully.");
    },
    onError: (error) => {
      const detail = error instanceof ApiError && typeof error.body === "object" && error.body && "detail" in error.body
        ? String((error.body as { detail: unknown }).detail)
        : "Unable to save your profile. Please review the fields and try again.";
      setSuccess("");
      setFailure(detail);
      toast.error("Profile could not be saved.");
    },
  });

  if (profileQuery.isPending) return <Workspace view="profile"><Panel><p data-testid="profile-loading-state" className="text-sm font-semibold text-slate-500">Loading your saved profile…</p></Panel></Workspace>;
  if (profileQuery.error || !profileQuery.data) return <Workspace view="profile"><Panel><p data-testid="profile-error-state" className="text-sm font-semibold text-rose-700">Unable to load your profile. Please sign in again.</p></Panel></Workspace>;

  const current = draft ?? profileQuery.data;
  const isDemo = sessionQuery.data?.demo_mode === true;
  const update = (key: keyof Profile, value: string | number | boolean) => {
    setSuccess(""); setFailure(""); setDraft({ ...current, [key]: value });
  };
  const schoolLevel = current.education_level === "Class 10" || current.education_level === "Class 12";
  const scoreOptions = schoolLevel ? ["Percentage", "Grade"] : ["Percentage", "SGPA", "CGPA"];
  const updateEducationLevel = (educationLevel: Profile["education_level"]) => {
    const allowed = educationLevel === "Class 10" || educationLevel === "Class 12" ? ["Percentage", "Grade"] : ["Percentage", "SGPA", "CGPA"];
    const scoreType = allowed.includes(current.score_type) ? current.score_type : "Percentage";
    setSuccess(""); setFailure("");
    setDraft({ ...current, education_level: educationLevel, score_type: scoreType as Profile["score_type"], score_scale: scoreType === "Percentage" ? "100" : scoreType === "Grade" ? "Not applicable" : "10" });
  };
  const updateScoreType = (scoreType: Profile["score_type"]) => {
    setSuccess(""); setFailure("");
    setDraft({ ...current, score_type: scoreType, score_scale: scoreType === "Percentage" ? "100" : scoreType === "Grade" ? "Not applicable" : "10" });
  };
  const updateScoreValue = (value: string) => {
    const percentage = current.score_type === "Percentage" && value !== "" ? Number(value) : current.marks;
    setSuccess(""); setFailure(""); setDraft({ ...current, score_value: value, marks: Number.isFinite(percentage) ? percentage : current.marks });
  };
  const submit = (event: FormEvent) => { event.preventDefault(); if (!save.isPending) save.mutate(current); };

  return <Workspace view="profile">
    <div className="mb-8 flex flex-col justify-between gap-5 sm:flex-row sm:items-end"><div><p className="font-mono text-[10px] font-bold uppercase tracking-[.2em] text-teal-700">Student profile</p><h1 data-testid="page-heading" className="mt-2 font-heading text-3xl font-extrabold tracking-tight text-slate-950 sm:text-4xl">Your profile powers the matching</h1><p className="mt-2 max-w-2xl text-sm leading-6 text-slate-600">Saved values are used immediately across eligibility, dashboard statistics, readiness, and decision support.</p></div><span data-testid="profile-account-type" className={`rounded-full px-3 py-2 text-xs font-extrabold uppercase tracking-wider ${isDemo ? "bg-amber-100 text-amber-800" : "bg-teal-50 text-teal-800"}`}>{isDemo ? "Fictional demo profile" : "Personal profile"}</span></div>
    <form onSubmit={submit} className="grid gap-6 lg:grid-cols-[1.15fr_.85fr]">
      <Panel>
        <Section title="Academic information" icon={<GraduationCap className="size-5" />}><div className="grid gap-4 sm:grid-cols-2"><Field label="Full name" value={current.full_name} onChange={(v) => update("full_name", v)} testid="profile-full-name-input" /><SelectField label="Education level" value={current.education_level} onChange={(v) => updateEducationLevel(v as Profile["education_level"])} options={["Class 10", "Class 12", "Diploma", "Undergraduate Degree", "Postgraduate Degree", "Other"]} testid="profile-education-level-select" /><Field label="Course" value={current.course} onChange={(v) => update("course", v)} testid="profile-course-input" /><Field label="Branch / stream" value={current.branch} onChange={(v) => update("branch", v)} testid="profile-branch-input" /><Field label="Current year / semester" value={current.year} onChange={(v) => update("year", v)} testid="profile-year-input" /><SelectField label="Academic score type" value={current.score_type} onChange={(v) => updateScoreType(v as Profile["score_type"])} options={scoreOptions} testid="profile-score-type-select" /><Field label={`${current.score_type} value`} value={current.score_value} type={current.score_type === "Grade" ? "text" : "number"} onChange={updateScoreValue} testid="profile-score-value-input" />{(current.score_type === "CGPA" || current.score_type === "SGPA") && <SelectField label="Grading scale" value={current.score_scale} onChange={(v) => update("score_scale", v)} options={["10", "4"]} labels={["10-point scale", "4-point scale"]} testid="profile-score-scale-select" />}</div><p data-testid="profile-score-guidance" className="mt-4 rounded-xl bg-amber-50 px-4 py-3 text-xs leading-5 text-amber-900">{current.score_type === "Percentage" ? "Percentage-based scholarship rules can be checked directly against this value." : current.score_type === "Grade" ? "Letter grades are stored as entered. Percentage-based scholarship rules will show Review unless an official equivalence is available." : `${current.score_type} is stored on its stated scale. Vidyadwar will not assume a conversion to percentage; percentage-based rules will show Review.`}</p></Section>
        <Section title="Personal and scheme information" icon={<UserRound className="size-5" />}><div className="grid gap-4 sm:grid-cols-2"><Field label="State / domicile" value={current.state} onChange={(v) => update("state", v)} testid="profile-state-input" /><Field label="Category" value={current.category} onChange={(v) => update("category", v)} testid="profile-category-input" /><Field label="Gender" value={current.gender} onChange={(v) => update("gender", v)} testid="profile-gender-input" /><Field label="Disability status" value={current.disability_status} onChange={(v) => update("disability_status", v)} testid="profile-disability-input" /></div></Section>
        <Section title="Financial context" icon={<ShieldCheck className="size-5" />}><div className="grid gap-4 sm:grid-cols-2"><Field label="Annual family income" value={String(current.annual_income)} type="number" onChange={(v) => update("annual_income", Number(v))} testid="profile-income-input" /><Toggle label="Income certificate available" value={current.income_certificate} onChange={(v) => update("income_certificate", v)} testid="profile-income-certificate-toggle" /><Toggle label="Currently receiving scholarship" value={current.receiving_scholarship} onChange={(v) => update("receiving_scholarship", v)} testid="profile-scholarship-toggle" /><Toggle label="Currently receiving stipend" value={current.receiving_stipend} onChange={(v) => update("receiving_stipend", v)} testid="profile-stipend-toggle" /><Toggle label="Other financial benefit" value={current.other_benefit} onChange={(v) => update("other_benefit", v)} testid="profile-other-benefit-toggle" /></div></Section>
        {success && <div data-testid="profile-save-success" role="status" className="mb-4 flex items-center gap-2 rounded-xl border border-emerald-200 bg-emerald-50 px-4 py-3 text-sm font-bold text-emerald-800"><Check className="size-4" />{success}</div>}
        {failure && <div data-testid="profile-save-error" role="alert" className="mb-4 flex items-center gap-2 rounded-xl border border-rose-200 bg-rose-50 px-4 py-3 text-sm font-bold text-rose-800"><CircleAlert className="size-4" />{failure}</div>}
        <Button type="submit" data-testid="profile-save-button" disabled={save.isPending} className="h-11 bg-slate-950 px-5 text-white hover:bg-teal-700">{save.isPending ? "Saving profile…" : "Save profile"}<Check /></Button>
      </Panel>
      <Panel className="h-fit bg-slate-950 text-white"><p className="font-mono text-[10px] uppercase tracking-[.16em] text-teal-300">Persistent and personal</p><h2 className="mt-3 font-heading text-2xl font-extrabold">Your values stay with your account.</h2><p className="mt-4 text-sm leading-6 text-slate-300">Refresh, navigate, or sign out and return — this profile remains the source of truth for your scholarship journey.</p><div className="mt-8 space-y-4">{["Changes are stored for the signed-in user", "Eligibility is recalculated after save", "Aarav Demo Mode remains a separate profile"].map((text) => <div key={text} className="flex items-start gap-3 text-sm font-semibold text-slate-200"><Check className="mt-0.5 size-4 shrink-0 text-teal-300" />{text}</div>)}</div></Panel>
    </form>
  </Workspace>;
}

function Panel({ children, className = "" }: { children: ReactNode; className?: string }) { return <div className={`rounded-2xl border border-slate-200 bg-white p-5 shadow-sm ${className}`}>{children}</div>; }
function Section({ title, icon, children }: { title: string; icon: ReactNode; children: ReactNode }) { return <section className="mb-8 border-b border-slate-100 pb-8"><div className="mb-5 flex items-center gap-3"><div className="flex size-9 items-center justify-center rounded-xl bg-teal-50 text-teal-700">{icon}</div><h2 className="font-heading text-lg font-extrabold text-slate-950">{title}</h2></div>{children}</section>; }
function Field({ label, value, onChange, testid, type = "text" }: { label: string; value: string; onChange: (value: string) => void; testid: string; type?: string }) { return <label className="block text-sm font-semibold text-slate-700">{label}<input data-testid={testid} type={type} min={type === "number" ? 0 : undefined} step={type === "number" ? "any" : undefined} value={value} onChange={(event) => onChange(event.target.value)} className="mt-2 h-10 w-full rounded-xl border border-slate-200 bg-slate-50 px-3 text-sm outline-none focus:border-teal-500 focus:bg-white focus:ring-4 focus:ring-teal-500/10" /></label>; }
function SelectField({ label, value, onChange, options, labels, testid }: { label: string; value: string; onChange: (value: string) => void; options: string[]; labels?: string[]; testid: string }) { return <label className="block text-sm font-semibold text-slate-700">{label}<select data-testid={testid} value={value} onChange={(event) => onChange(event.target.value)} className="mt-2 h-10 w-full rounded-xl border border-slate-200 bg-slate-50 px-3 text-sm outline-none focus:border-teal-500 focus:bg-white focus:ring-4 focus:ring-teal-500/10">{options.map((option, index) => <option key={option} value={option}>{labels?.[index] ?? option}</option>)}</select></label>; }
function Toggle({ label, value, onChange, testid }: { label: string; value: boolean; onChange: (value: boolean) => void; testid: string }) { return <label className="flex items-center gap-3 rounded-xl border border-slate-200 p-3 text-sm font-semibold text-slate-700"><input data-testid={testid} type="checkbox" checked={value} onChange={(event) => onChange(event.target.checked)} className="size-4 accent-teal-700" />{label}</label>; }