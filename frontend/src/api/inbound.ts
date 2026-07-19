export interface PitchSubmissionResponse {
  status: string;
  person_id: string;
  opportunity_id: string;
}

export async function submitPitch(formData: FormData, signal?: AbortSignal): Promise<PitchSubmissionResponse> {
  const response = await fetch("/api/v1/inbound/pitch", {
    method: "POST",
    body: formData,
    signal,
  });

  if (!response.ok) {
    throw new Error(`Submit pitch failed with status ${response.status}`);
  }

  return await response.json() as PitchSubmissionResponse;
}
