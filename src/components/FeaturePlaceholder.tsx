export function FeaturePlaceholder() {
  return (
    <section
      id="compare"
      aria-labelledby="feature-heading"
      className="rounded-lg border border-dashed border-slate-300 bg-slate-50 p-12 text-center"
    >
      <h2 id="feature-heading" className="text-base font-medium text-slate-900">
        Comparison workspace
      </h2>
      <p className="mx-auto mt-2 max-w-md text-sm text-slate-500">
        The pairwise comparison view will live here — two options side by side,
        one choice at a time.
      </p>
    </section>
  );
}
