interface PlaceholderPageProps {
  label: string;
}

export function PlaceholderPage({ label }: PlaceholderPageProps) {
  return (
    <div className="flex flex-col items-center justify-center min-h-[60vh] text-center">
      <h2 className="text-xl font-semibold text-ink mb-2">{label}</h2>
      <p className="text-sm text-muted-2">Coming soon</p>
    </div>
  );
}
