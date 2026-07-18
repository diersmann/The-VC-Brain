import { ApiStatus } from "./components/ApiStatus";

const systems = ["Sourcing", "Evidence", "Scoring", "Decisions"];

export default function App() {
  return (
    <div className="min-h-screen bg-slate-50 px-6 py-12">
      <div className="mx-auto flex max-w-4xl flex-col gap-8">
        <header className="flex flex-wrap items-start justify-between gap-4">
          <div>
            <p className="text-sm font-semibold text-blue-700">THE VC BRAIN</p>
            <h1 className="text-3xl font-bold tracking-tight text-gray-900">
              Evidence-backed founder intelligence
            </h1>
          </div>
          <ApiStatus />
        </header>

        <main className="rounded-2xl border border-gray-200 bg-white p-8 shadow-sm">
          <div className="flex flex-col gap-6">
            <h2 className="text-xl font-semibold text-gray-900">Development stack is ready</h2>
            <p className="leading-relaxed text-gray-600">
              This boilerplate connects a Vite and Tailwind CSS frontend to a FastAPI modular
              monolith, background worker, PostgreSQL with pgvector, Redis, and MinIO.
            </p>
            <div className="flex flex-wrap gap-2">
              {systems.map((system) => (
                <span
                  key={system}
                  className="rounded-full bg-blue-50 px-4 py-1.5 text-sm font-medium text-blue-700"
                >
                  {system}
                </span>
              ))}
            </div>
          </div>
        </main>
      </div>
    </div>
  );
}
