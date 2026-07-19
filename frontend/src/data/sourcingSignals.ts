import type { Candidate } from "../types/candidate";

export function hasHighMultiAxisSignal(candidate: Candidate): boolean {
  const values = [
    candidate.scores?.founder ?? candidate.scores?.raw?.founder,
    candidate.scores?.market ?? candidate.scores?.raw?.market,
    candidate.scores?.idea_market ?? candidate.scores?.raw?.idea_market,
  ];
  return values.every((value) => typeof value === "number" && value >= .67);
}
