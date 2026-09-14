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
        The evaluation view will live here — two groups or teammates side by
        side, rated on a 6-point scale.
      </p>
    </section>
  );
}
