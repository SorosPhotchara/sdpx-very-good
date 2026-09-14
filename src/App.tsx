import { Navbar } from "./components/Navbar";
import { FeaturePlaceholder } from "./components/FeaturePlaceholder";

export function App() {
  return (
    <div className="min-h-screen bg-white text-slate-900">
      <Navbar />

      <main className="mx-auto max-w-4xl px-6 py-16">
        <header className="text-center">
          <h1 className="text-4xl font-semibold tracking-tight sm:text-5xl">
            Pairwise
          </h1>
          <p className="mt-3 text-lg text-slate-600">
            Rank what matters, one comparisons at a time — for university
            courses, projects, and peer review.
          </p>

          <a
            data-testid="cta-primary"
            href="#compare"
            className="mt-8 inline-block rounded-md bg-slate-900 px-6 py-3 text-sm font-medium text-white transition-colors hover:bg-slate-700"
          >
            Start comparing
          </a>
        </header>

        <div className="mt-16">
          <FeaturePlaceholder />
        </div>
      </main>
    </div>
  );
}
