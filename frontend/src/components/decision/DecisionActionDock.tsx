import { useState } from "react";
import { CheckCircle2, PauseCircle, Scale, X, XCircle } from "lucide-react";

import { recordCandidateDecision, type DecisionAction } from "../../api/candidates";

const actions: { value: DecisionAction; label: string; prompt: string; style: string; icon: React.ElementType }[] = [
  { value: "proceed", label: "Proceed", prompt: "Why should the fund move forward?", style: "bg-[#e4f2ed] text-[#347c67]", icon: CheckCircle2 },
  { value: "hold", label: "Hold", prompt: "What needs to change or be verified?", style: "bg-[#fff1df] text-[#a96e2d]", icon: PauseCircle },
  { value: "decline", label: "Decline", prompt: "Record the evidence-backed reason for declining.", style: "bg-[#fbe8e9] text-[#b65d5d]", icon: XCircle },
];

export function DecisionActionDock({
  candidateId,
  opportunityId,
  currentState,
  onSaved,
}: {
  candidateId: string;
  opportunityId: string | null;
  currentState: string;
  onSaved: () => void | Promise<void>;
}) {
  const [selected, setSelected] = useState<DecisionAction | null>(null);
  const [reason, setReason] = useState("");
  const [status, setStatus] = useState<"idle" | "saving" | "error">("idle");
  const [confirmation, setConfirmation] = useState<string | null>(null);
  const activeAction = actions.find((item) => item.value === selected);

  const saveDecision = async () => {
    if (!selected || !opportunityId || reason.trim().length < 3) return;
    setStatus("saving");
    try {
      const result = await recordCandidateDecision(candidateId, opportunityId, selected, reason.trim());
      setConfirmation(`Decision saved · ${result.new_state}`);
      setSelected(null);
      setReason("");
      setStatus("idle");
      await onSaved();
      window.setTimeout(() => setConfirmation(null), 2800);
    } catch {
      setStatus("error");
    }
  };

  return (
    <>
      {(activeAction || confirmation) && (
        <div className="fixed bottom-24 right-4 z-[60] w-[min(420px,calc(100vw-2rem))] sm:right-6">
          {confirmation ? (
            <div className="flex items-center gap-2 rounded-lg bg-[#e4f2ed]/95 px-4 py-3 text-xs font-bold text-success shadow-[0_16px_45px_rgba(40,78,67,.2)] backdrop-blur-xl">
              <CheckCircle2 className="h-4 w-4" />{confirmation}
            </div>
          ) : activeAction ? (
            <section className="rounded-lg bg-white/95 p-4 shadow-[0_20px_60px_rgba(31,45,66,.22)] backdrop-blur-2xl" aria-label={`${activeAction.label} decision reason`}>
              <div className="flex items-start justify-between gap-3">
                <div><div className="eyebrow mb-1">Human decision</div><h2 className="text-sm font-bold">{activeAction.label} this opportunity</h2></div>
                <button type="button" onClick={() => { setSelected(null); setStatus("idle"); }} aria-label="Close decision reason" className="rounded-md bg-surface-2 p-1.5 text-muted"><X className="h-3.5 w-3.5" /></button>
              </div>
              <label className="mt-3 block"><span className="mb-2 block text-xs font-semibold text-muted">{activeAction.prompt}</span><textarea value={reason} onChange={(event) => setReason(event.target.value)} rows={3} autoFocus maxLength={2000} placeholder="Add a concise reason for the decision record…" className="w-full resize-none rounded-md bg-surface-2 px-3 py-2.5 text-sm leading-5 outline-none focus:ring-2 focus:ring-accent/20" /></label>
              {status === "error" && <div className="mt-2 text-xs font-semibold text-danger">Unable to save the decision. Please retry.</div>}
              <div className="mt-3 flex items-center justify-between gap-3">
                <span className="text-[10px] text-muted">Current state: <strong className="text-ink-2">{currentState}</strong></span>
                <button type="button" onClick={() => void saveDecision()} disabled={status === "saving" || reason.trim().length < 3} className={`rounded-md px-4 py-2.5 text-xs font-bold transition disabled:opacity-40 ${activeAction.style}`}>{status === "saving" ? "Saving…" : `Confirm ${activeAction.label}`}</button>
              </div>
            </section>
          ) : null}
        </div>
      )}

      <div className="fixed bottom-4 right-4 z-[60] flex items-center gap-1.5 rounded-lg bg-white/88 p-2 shadow-[0_18px_55px_rgba(31,45,66,.2)] backdrop-blur-2xl sm:bottom-6 sm:right-6">
        <span className="hidden items-center gap-1.5 px-2 text-[10px] font-bold uppercase tracking-wider text-muted sm:inline-flex"><Scale className="h-3.5 w-3.5 text-accent" /> Decide</span>
        <span className="hidden items-center gap-1.5 rounded-md bg-surface-2 px-2.5 py-2 text-[9px] font-bold uppercase tracking-wider text-muted lg:inline-flex"><span className="h-1.5 w-1.5 rounded-full bg-accent-muted" />{formatState(currentState)}</span>
        {actions.map((action) => {
          const Icon = action.icon;
          return <button key={action.value} type="button" disabled={!opportunityId} title={!opportunityId ? "No opportunity is linked to this candidate" : undefined} aria-pressed={selected === action.value} onClick={() => { setSelected(action.value); setStatus("idle"); }} className={`inline-flex items-center gap-1.5 rounded-md px-3 py-2.5 text-xs font-bold transition hover:-translate-y-0.5 disabled:cursor-not-allowed disabled:opacity-40 ${action.style} ${selected === action.value ? "ring-2 ring-current ring-offset-1" : ""}`}><Icon className="h-3.5 w-3.5" />{action.label}</button>;
        })}
      </div>
    </>
  );
}

function formatState(value: string): string {
  return value.replace(/[_-]+/g, " ");
}
