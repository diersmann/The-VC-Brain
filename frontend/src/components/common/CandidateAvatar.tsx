import { useState } from "react";

import { initials } from "../../data/candidateProfile";

interface CandidateAvatarProps {
  name: string | null;
  avatarUrl?: string | null;
  className?: string;
  imageClassName?: string;
}

export function CandidateAvatar({
  name,
  avatarUrl,
  className = "",
  imageClassName = "",
}: CandidateAvatarProps) {
  const [failed, setFailed] = useState(false);
  return (
    <span className={`inline-flex shrink-0 items-center justify-center overflow-hidden ${className}`}>
      {avatarUrl && !failed ? (
        <img
          src={avatarUrl}
          alt={`${name ?? "Candidate"} avatar`}
          className={`h-full w-full object-cover ${imageClassName}`}
          loading="lazy"
          onError={() => setFailed(true)}
        />
      ) : (
        initials(name)
      )}
    </span>
  );
}
