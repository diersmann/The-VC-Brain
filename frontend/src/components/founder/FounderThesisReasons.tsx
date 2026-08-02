import type { ElementType } from "react";

export function FounderThesisReasons({ icon: Icon, label, values, tone }: { icon: ElementType; label: string; values: string[]; tone: "green" | "amber" | "blue" }) {
  const colors = { green: "bg-[#e4f2ed] text-[#347c67]", amber: "bg-[#fff1df] text-[#a96e2d]", blue: "bg-[#e7eef9] text-[#5074a8]" };
  return <div className={`rounded-md p-3.5 ${colors[tone]}`}><div className="flex items-center gap-2 text-[10px] font-bold uppercase tracking-wider"><Icon className="h-3.5 w-3.5" />{label}</div><div className="mt-2 text-xs font-semibold">{values.length ? values.join(" · ") : "None"}</div></div>;
}
