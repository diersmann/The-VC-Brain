import type { CandidateDetail } from "../types/candidate";

export type CandidateLinkKind = "linkedin" | "github" | "website" | "deck" | "x";

export interface CandidateExternalLink {
  kind: CandidateLinkKind;
  label: string;
  url: string;
}

export function candidateExternalLinks(candidate: CandidateDetail): CandidateExternalLink[] {
  const links: CandidateExternalLink[] = [];
  const handles = candidate.handles ?? {};

  addLink(links, "linkedin", "LinkedIn", handleUrl(handles.linkedin, "linkedin"));
  addLink(
    links,
    "linkedin",
    "LinkedIn",
    sourceUrl(candidate, (url) => url.hostname.endsWith("linkedin.com") && url.pathname.startsWith("/in/")),
  );

  addLink(links, "github", "GitHub", handleUrl(handles.github, "github"));
  const githubLogin = observationValue(candidate, "github_login");
  addLink(links, "github", "GitHub", githubLogin ? `https://github.com/${encodeURIComponent(githubLogin)}` : null);
  addLink(
    links,
    "github",
    "GitHub",
    sourceUrl(candidate, (url) => url.hostname === "github.com" && url.pathname.split("/").filter(Boolean).length === 1),
  );

  addLink(links, "website", "Website", safeUrl(candidate.profile?.website));
  addLink(links, "deck", "Pitch deck", safeUrl(candidate.profile?.deck_url));
  addLink(links, "x", "X / Twitter", handleUrl(handles.twitter ?? handles.x, "x"));

  return links;
}

function addLink(
  links: CandidateExternalLink[],
  kind: CandidateLinkKind,
  label: string,
  url: string | null,
): void {
  if (!url || links.some((link) => link.kind === kind)) return;
  links.push({ kind, label, url });
}

function handleUrl(value: string | undefined, platform: "linkedin" | "github" | "x"): string | null {
  if (!value?.trim()) return null;
  const handle = value.trim().replace(/^@/, "");
  if (/^https?:\/\//i.test(handle)) return safeUrl(handle);
  if (handle.includes("linkedin.com/in/")) return safeUrl(`https://${handle}`);
  if (handle.includes("github.com/")) return safeUrl(`https://${handle}`);
  if (platform === "linkedin") return `https://www.linkedin.com/in/${encodeURIComponent(handle)}`;
  if (platform === "github") return `https://github.com/${encodeURIComponent(handle)}`;
  return `https://x.com/${encodeURIComponent(handle)}`;
}

function sourceUrl(candidate: CandidateDetail, matches: (url: URL) => boolean): string | null {
  for (const observation of candidate.observations) {
    const url = parsedUrl(observation.source_uri);
    if (url && matches(url)) return url.toString();
  }
  return null;
}

function observationValue(candidate: CandidateDetail, predicate: string): string | null {
  return candidate.observations.find((item) => item.predicate === predicate)?.object_value ?? null;
}

function safeUrl(value: string | null | undefined): string | null {
  if (!value) return null;
  const normalized = /^https?:\/\//i.test(value) ? value : `https://${value}`;
  const parsed = parsedUrl(normalized);
  return parsed?.toString() ?? null;
}

function parsedUrl(value: string): URL | null {
  try {
    const url = new URL(value);
    return url.protocol === "http:" || url.protocol === "https:" ? url : null;
  } catch {
    return null;
  }
}
