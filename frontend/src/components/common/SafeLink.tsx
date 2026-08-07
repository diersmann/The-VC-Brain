import type { AnchorHTMLAttributes, ReactNode } from "react";

import { safeActionUrl } from "../../data/candidateLinks";

export interface SafeLinkProps extends Omit<AnchorHTMLAttributes<HTMLAnchorElement>, "href" | "target" | "rel"> {
  href: string | null | undefined;
  allowMailto?: boolean;
  children?: ReactNode;
}

/**
 * Render an actionable link only after applying the shared external-link
 * policy. Invalid or unsupported destinations render no interactive element.
 */
export function SafeLink({ href, allowMailto = false, children, ...props }: SafeLinkProps) {
  const safeHref = safeActionUrl(href, { allowMailto });
  if (!safeHref) return null;
  const isHttp = /^https?:\/\//i.test(safeHref);
  return <a {...props} href={safeHref} {...(isHttp ? { target: "_blank", rel: "noreferrer" } : {})}>{children}</a>;
}
