export interface Option {
  label: string;
  value: string;
  description?: string;
}

export const stages: Option[] = [
  { label: "Pre-seed", value: "pre-seed", description: "Idea to first signals" },
  { label: "Seed", value: "seed", description: "Early product-market proof" },
  { label: "Series A", value: "series-a", description: "Repeatable growth" },
];

export const sectors: Option[] = [
  { label: "AI & Infrastructure", value: "ai" },
  { label: "Climate Tech", value: "climate" },
  { label: "Deep Tech", value: "deep-tech" },
  { label: "B2B Software", value: "b2b" },
  { label: "Fintech", value: "fintech" },
  { label: "Health & Biotech", value: "health" },
];

export const regions: Option[] = [
  { label: "DACH", value: "dach" },
  { label: "Europe", value: "europe" },
  { label: "United Kingdom", value: "uk" },
  { label: "United States", value: "us" },
  { label: "Global", value: "global" },
];

export const checks: Option[] = [
  { label: "€100k – €250k", value: "100-250" },
  { label: "€250k – €500k", value: "250-500" },
  { label: "€500k – €1m", value: "500-1000" },
  { label: "€1m+", value: "1000+" },
];

export function checkRange(value: string): [number | null, number | null] {
  if (value === "100-250") return [100, 250];
  if (value === "250-500") return [250, 500];
  if (value === "500-1000") return [500, 1000];
  return [1000, null];
}

export function checkBand(minimum: number | null, maximum: number | null): string {
  if (minimum === 100 && maximum === 250) return "100-250";
  if (minimum === 500 && maximum === 1000) return "500-1000";
  if (minimum === 1000 && maximum == null) return "1000+";
  return "250-500";
}

export function toggleValue(values: string[], value: string): string[] {
  return values.includes(value) ? values.filter((item) => item !== value) : [...values, value];
}

export function labelsFor(options: Option[], values: string[]): string {
  return options.filter((option) => values.includes(option.value)).map((option) => option.label).join(", ");
}
