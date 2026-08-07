import { useEffect, useRef, useState } from "react";
import { Check, Copy, ExternalLink, FileQuestion, Mail, MessageSquareText, Send, Sparkles, X } from "lucide-react";

import { draftCandidateOutreach, type OutreachDraft, type OutreachEmailType } from "../../api/candidates";
import { safeMailto } from "../../data/candidateLinks";
import type { Candidate } from "../../types/candidate";
import { CandidateAvatar } from "../common/CandidateAvatar";
import { SafeLink } from "../common/SafeLink";

const emailTypes: { value: OutreachEmailType; label: string; description: string }[] = [
  { value: "founder_intro", label: "Founder intro", description: "Warm, low-pressure first contact" },
  { value: "request_deck", label: "Request deck", description: "Ask for deck or product overview" },
  { value: "diligence", label: "Diligence", description: "Clarify evidence and open questions" },
  { value: "follow_up", label: "Follow-up", description: "Continue an existing conversation" },
];

export function OutreachComposer({ candidate, onClose }: { candidate: Candidate; onClose: () => void }) {
  const dialogRef = useRef<HTMLElement>(null);
  const closeButtonRef = useRef<HTMLButtonElement>(null);
  const restoreFocusRef = useRef<HTMLElement | null>(null);
  const onCloseRef = useRef(onClose);
  const [emailType, setEmailType] = useState<OutreachEmailType>("founder_intro");
  const [brief, setBrief] = useState("");
  const [draft, setDraft] = useState<OutreachDraft | null>(null);
  const [subject, setSubject] = useState("");
  const [body, setBody] = useState("");
  const [status, setStatus] = useState<"idle" | "drafting" | "error" | "copied">("idle");
  const [approved, setApproved] = useState(false);

  useEffect(() => {
    onCloseRef.current = onClose;
  }, [onClose]);

  useEffect(() => {
    restoreFocusRef.current = document.activeElement instanceof HTMLElement ? document.activeElement : null;
    closeButtonRef.current?.focus();

    const handleKeyDown = (event: KeyboardEvent) => {
      if (event.key === "Escape") {
        event.preventDefault();
        onCloseRef.current();
        return;
      }
      if (event.key !== "Tab" || !dialogRef.current) return;
      const focusable = Array.from(dialogRef.current.querySelectorAll<HTMLElement>(
        "button:not([disabled]), input:not([disabled]), textarea:not([disabled]), a[href]",
      ));
      if (!focusable.length) return;
      const first = focusable[0];
      const last = focusable[focusable.length - 1];
      const currentIndex = focusable.indexOf(document.activeElement as HTMLElement);
      if (currentIndex === -1) {
        event.preventDefault();
        (event.shiftKey ? last : first).focus();
      } else if (event.shiftKey && currentIndex === 0) {
        event.preventDefault();
        last.focus();
      } else if (!event.shiftKey && currentIndex === focusable.length - 1) {
        event.preventDefault();
        first.focus();
      }
    };

    document.addEventListener("keydown", handleKeyDown);
    return () => {
      document.removeEventListener("keydown", handleKeyDown);
      restoreFocusRef.current?.focus();
    };
  }, []);

  useEffect(() => {
    setApproved(false);
  }, [candidate.email, candidate.consent_state]);

  const generateDraft = async () => {
    setStatus("drafting");
    setApproved(false);
    try {
      const nextDraft = await draftCandidateOutreach(candidate.id, emailType, brief);
      setDraft(nextDraft);
      setSubject(nextDraft.subject);
      setBody(nextDraft.body);
      setApproved(false);
      setStatus("idle");
    } catch {
      setStatus("error");
    }
  };

  const copyDraft = async () => {
    await navigator.clipboard.writeText(`Subject: ${subject}\n\n${body}`);
    setStatus("copied");
    window.setTimeout(() => setStatus("idle"), 1800);
  };

  const mailto = safeMailto(candidate.email, subject, body);
  const suppressionReason = candidate.email
    ? ["opted_out", "suppressed", "do_not_contact"].includes(candidate.consent_state)
      ? `Suppressed by consent state: ${candidate.consent_state}`
      : mailto
        ? null
        : "No verified recipient email"
    : "No verified recipient email";

  return (
    <div className="fixed inset-0 z-[70] flex justify-end bg-[#172235]/25 p-3 backdrop-blur-sm sm:p-5" role="presentation" onMouseDown={onClose}>
      <section
        ref={dialogRef}
        role="dialog"
        aria-modal="true"
        aria-label={`Draft outreach to ${candidate.display_name ?? "founder"}`}
        className="flex h-full w-full max-w-[560px] flex-col overflow-hidden rounded-lg bg-[#f7f9fc]/95 shadow-[0_24px_80px_rgba(31,45,66,.28)] backdrop-blur-2xl"
        onMouseDown={(event) => event.stopPropagation()}
      >
        <header className="flex items-center justify-between gap-3 bg-gradient-to-r from-[#e7eef9] to-[#eef6f3] px-5 py-4">
          <div className="flex min-w-0 items-center gap-3">
            <CandidateAvatar name={candidate.display_name} avatarUrl={candidate.avatar_url} className="h-10 w-10 rounded-md bg-accent text-xs font-bold text-white" />
            <div className="min-w-0">
              <div className="eyebrow mb-1">Human-reviewed outreach</div>
              <h2 className="truncate text-base font-bold">Write to {candidate.display_name ?? candidate.stable_id}</h2>
            </div>
          </div>
          <button ref={closeButtonRef} type="button" onClick={onClose} aria-label="Close outreach composer" className="rounded-md bg-white/65 p-2 text-muted hover:text-ink"><X className="h-4 w-4" /></button>
        </header>

        <div className="flex-1 overflow-y-auto p-5">
          <div className="data-label mb-2">Choose an email type</div>
          <div className="grid grid-cols-2 gap-2">
            {emailTypes.map((option) => {
              const selected = option.value === emailType;
              return (
                <button
                  key={option.value}
                  type="button"
                  aria-pressed={selected}
                  onClick={() => { setEmailType(option.value); setApproved(false); }}
                  className={`rounded-md p-3 text-left transition ${selected ? "bg-accent text-white shadow-md" : "bg-white/75 text-ink-2 hover:bg-white"}`}
                >
                  <div className="flex items-center justify-between gap-2 text-xs font-bold"><span>{option.label}</span>{selected && <Check className="h-3.5 w-3.5" />}</div>
                  <div className={`mt-1 text-[10px] leading-4 ${selected ? "text-white/75" : "text-muted"}`}>{option.description}</div>
                </button>
              );
            })}
          </div>

          <label className="mt-5 block">
            <span className="mb-2 flex items-center gap-1.5 text-xs font-bold text-ink-2"><MessageSquareText className="h-3.5 w-3.5 text-accent" />Describe the email in one sentence</span>
            <input
              value={brief}
              onChange={(event) => { setBrief(event.target.value); setApproved(false); }}
              maxLength={600}
              placeholder="e.g. Mention their AI infrastructure work and ask about enterprise traction."
              className="w-full rounded-md bg-white px-3.5 py-3 text-sm shadow-inner shadow-slate-200/70 outline-none focus:ring-2 focus:ring-accent/20"
            />
          </label>

          <button
            type="button"
            onClick={() => void generateDraft()}
            disabled={status === "drafting"}
            className="mt-4 flex w-full items-center justify-center gap-2 rounded-md bg-accent px-4 py-3 text-sm font-bold text-white transition hover:bg-[#344c6c] disabled:opacity-60"
          >
            <Sparkles className="h-4 w-4" />{status === "drafting" ? "Email agent is drafting…" : draft ? "Regenerate with email agent" : "Draft with email agent"}
          </button>
          {status === "error" && <div className="mt-3 rounded-md bg-[#fbe8e9] px-3 py-2 text-xs font-semibold text-danger">Unable to create the draft. Check the API service and retry.</div>}

          <div className="mt-5 rounded-lg bg-[#eef3f8] p-4 text-xs text-ink-2">
            <div className="data-label mb-2">Contact safeguards</div>
            <div className="grid gap-2 sm:grid-cols-2">
              <div><span className="font-bold">Provenance:</span> {candidate.origin ?? "Unclassified"}{candidate.profile?.source_types.length ? ` · ${candidate.profile.source_types.join(", ")}` : " · No source type recorded"}</div>
              <div><span className="font-bold">Consent:</span> {candidate.consent_state}</div>
            </div>
            <div className="mt-2"><span className="font-bold">Provider state:</span> Draft only · not sent; delivery and replies are not connected.</div>
            {suppressionReason && <div className="mt-3 rounded-md bg-[#fff1df] px-3 py-2 font-semibold text-[#946225]">{suppressionReason}. Manual email handoff is disabled.</div>}
          </div>

          {draft && (
            <div className="mt-5 space-y-4 rounded-lg bg-white/70 p-4 shadow-[0_12px_30px_rgba(70,91,120,.08)]">
              <div className="flex flex-wrap items-center justify-between gap-2">
                <div className="flex items-center gap-2 text-xs font-bold"><Mail className="h-4 w-4 text-accent" />Editable email draft</div>
                <span className={`status-pill ${draft.generation_mode === "agent" ? "bg-[#e4f2ed] text-success" : "bg-[#fff1df] text-warn"}`}>
                  {draft.generation_mode === "agent" ? `AI agent · ${draft.model ?? "configured model"}` : "Local template"}
                </span>
              </div>
              {draft.warning && <div className="rounded-md bg-[#fff1df] px-3 py-2 text-[11px] leading-5 text-[#946225]">{draft.warning}</div>}
              <label className="block"><span className="data-label mb-1.5 block">Subject</span><input value={subject} onChange={(event) => { setSubject(event.target.value); setApproved(false); }} className="w-full rounded-md bg-surface-2 px-3 py-2.5 text-sm font-semibold outline-none focus:ring-2 focus:ring-accent/20" /></label>
              <label className="block"><span className="data-label mb-1.5 block">Body</span><textarea value={body} onChange={(event) => { setBody(event.target.value); setApproved(false); }} rows={10} className="w-full resize-y rounded-md bg-surface-2 px-3 py-3 text-sm leading-6 outline-none focus:ring-2 focus:ring-accent/20" /></label>
              <label className={`flex items-start gap-2 rounded-md p-3 ${suppressionReason ? "bg-[#fff1df]" : "bg-[#e4f2ed]"}`}>
                <input type="checkbox" checked={approved} onChange={(event) => setApproved(event.target.checked)} disabled={Boolean(suppressionReason)} className="mt-0.5 h-4 w-4 accent-accent" />
                <span className="text-[11px] leading-5"><span className="font-bold">I approve this edited draft for manual handoff.</span><br />This does not claim provider delivery or a reply.</span>
              </label>
            </div>
          )}
        </div>

        {draft && (
          <footer className="flex flex-wrap items-center gap-2 bg-white/75 px-5 py-4 shadow-[0_-8px_24px_rgba(70,91,120,.06)]">
            <button type="button" onClick={() => void copyDraft()} className="inline-flex items-center gap-2 rounded-md bg-surface-2 px-4 py-2.5 text-xs font-bold text-ink-2"><Copy className="h-3.5 w-3.5" />{status === "copied" ? "Copied" : "Copy draft"}</button>
            {mailto && !suppressionReason ? approved ? <SafeLink role="link" href={mailto} allowMailto className="ml-auto inline-flex items-center gap-2 rounded-md bg-accent px-4 py-2.5 text-xs font-bold text-white"><Send className="h-3.5 w-3.5" />Open in email<ExternalLink className="h-3 w-3" /></SafeLink> : <span role="link" aria-disabled="true" className="ml-auto inline-flex cursor-not-allowed items-center gap-2 rounded-md bg-accent/40 px-4 py-2.5 text-xs font-bold text-white"><Send className="h-3.5 w-3.5" />Approve to hand off<ExternalLink className="h-3 w-3" /></span> : <span className="ml-auto inline-flex items-center gap-1.5 text-[11px] font-semibold text-muted"><FileQuestion className="h-3.5 w-3.5" />No verified email; copy the draft manually.</span>}
          </footer>
        )}
      </section>
    </div>
  );
}
