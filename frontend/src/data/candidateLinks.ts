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

  addLink(links, "website", "Website", safeExternalUrl(candidate.profile?.website));
  addLink(links, "deck", "Pitch deck", safeExternalUrl(candidate.profile?.deck_url));
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
  if (/^https?:\/\//i.test(handle)) return safeExternalUrl(handle);
  if (handle.includes("linkedin.com/in/")) return safeExternalUrl(`https://${handle}`);
  if (handle.includes("github.com/")) return safeExternalUrl(`https://${handle}`);
  if (platform === "linkedin") return `https://www.linkedin.com/in/${encodeURIComponent(handle)}`;
  if (platform === "github") return `https://github.com/${encodeURIComponent(handle)}`;
  return `https://x.com/${encodeURIComponent(handle)}`;
}

function sourceUrl(candidate: CandidateDetail, matches: (url: URL) => boolean): string | null {
  for (const observation of candidate.observations) {
    const url = parsedUrl(observation.source_uri);
    if (url && matches(url)) return safeHttpUrl(url.toString());
  }
  return null;
}

function observationValue(candidate: CandidateDetail, predicate: string): string | null {
  return candidate.observations.find((item) => item.predicate === predicate)?.object_value ?? null;
}

export function safeExternalUrl(value: string | null | undefined): string | null {
  if (!value) return null;
  const trimmed = value.trim();
  if (!trimmed || /^[a-z][a-z\d+.-]*:/i.test(trimmed) && !/^https?:\/\//i.test(trimmed)) return null;
  const normalized = /^https?:\/\//i.test(trimmed) ? trimmed : `https://${trimmed}`;
  return safeHttpUrl(normalized);
}

export function safeHttpUrl(value: string | null | undefined): string | null {
  if (!value || !/^https?:\/\//i.test(value.trim())) return null;
  const parsed = parsedUrl(value.trim());
  return parsed?.toString() ?? null;
}

const mailtoRecipientPattern = /^[A-Za-z0-9!$'*+/^_`{|}~-]+(?:\.[A-Za-z0-9!$'*+/^_`{|}~-]+)*@[A-Za-z0-9](?:[A-Za-z0-9-]{0,61}[A-Za-z0-9])?(?:\.[A-Za-z0-9](?:[A-Za-z0-9-]{0,61}[A-Za-z0-9])?)+$/;

/**
 * Build the manual email-client handoff without allowing recipient header
 * injection. Subject and body are URI components; HTTP URL policy is kept
 * separate in safeExternalUrl/safeHttpUrl.
 */
export function safeMailto(
  recipient: string | null | undefined,
  subject: string,
  body: string,
): string | null {
  if (!recipient || hasControlCharacter(recipient)) return null;
  const normalizedRecipient = recipient.trim();
  if (!mailtoRecipientPattern.test(normalizedRecipient)) return null;

  try {
    const atIndex = normalizedRecipient.lastIndexOf("@");
    const localPart = normalizedRecipient.slice(0, atIndex);
    if (localPart.length > 64 || normalizedRecipient.length > 254) return null;
    const encodedLocalPart = encodeURIComponent(normalizedRecipient.slice(0, atIndex));
    const domain = normalizedRecipient.slice(atIndex + 1);
    return `mailto:${encodedLocalPart}@${domain}?subject=${encodeURIComponent(subject)}&body=${encodeURIComponent(body)}`;
  } catch {
    return null;
  }
}

function hasControlCharacter(value: string): boolean {
  for (let index = 0; index < value.length; index += 1) {
    const code = value.charCodeAt(index);
    if (code <= 0x1f || code === 0x7f) return true;
  }
  return false;
}

function parsedUrl(value: string): URL | null {
  try {
    const url = new URL(value);
    return url.protocol === "http:" || url.protocol === "https:" ? url : null;
  } catch {
    return null;
  }
}
