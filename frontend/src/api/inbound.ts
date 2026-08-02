export interface PitchSubmissionResponse {
  status: string;
  person_id: string;
  opportunity_id: string;
}

export async function submitPitch(
  formData: FormData,
  signal?: AbortSignal,
  idempotencyKey?: string,
): Promise<PitchSubmissionResponse> {
  const response = await fetch("/api/v1/inbound/pitch", {
    method: "POST",
    body: formData,
    signal,
    headers: idempotencyKey ? { "Idempotency-Key": idempotencyKey } : undefined,
  });

  if (!response.ok) {
    throw new Error(`Submit pitch failed with status ${response.status}`);
  }

  return await response.json() as PitchSubmissionResponse;
}
