import { useState } from "react";
import { importRoster as importRosterFromApi, previewRoster } from "../lib/api";
import type { RosterRow } from "../domain/roster";

const EXAMPLE_ROSTER = "email,group_name\nstudent@uni.ac.th,Aurora";
const API_UNREACHABLE_ERROR = "Could not reach the roster API. Is the backend running?";

export function FeaturePlaceholder() {
  const [csvText, setCsvText] = useState(EXAMPLE_ROSTER);
  const [rows, setRows] = useState<RosterRow[]>([]);
  const [errors, setErrors] = useState<string[]>([]);
  const [publishedCount, setPublishedCount] = useState<number | null>(null);
  const [isBusy, setIsBusy] = useState(false);

  async function importRoster() {
    setIsBusy(true);
    try {
      const result = await importRosterFromApi(csvText);
      setRows(result.rows);
      setErrors(result.errors);
      setPublishedCount(null);
    } catch {
      setRows([]);
      setErrors([API_UNREACHABLE_ERROR]);
    } finally {
      setIsBusy(false);
    }
  }

  async function publish() {
    setIsBusy(true);
    try {
      const assignments = await previewRoster(rows);
      setPublishedCount(assignments.length);
    } catch {
      setErrors([API_UNREACHABLE_ERROR]);
    } finally {
      setIsBusy(false);
    }
  }

  return (
    <section
      id="compare"
      aria-labelledby="feature-heading"
      data-testid="comparison-workspace"
      className="rounded-lg border border-slate-300 bg-slate-50 p-8"
    >
      <div className="text-center">
        <h2 id="feature-heading" className="text-base font-medium text-slate-900">
          Comparison workspace
        </h2>
        <p className="mx-auto mt-2 max-w-md text-sm text-slate-500">
          Import a class roster to preview fair pairwise comparisons.
        </p>
      </div>

      <label className="mt-6 block text-sm font-medium text-slate-700" htmlFor="roster-csv">
        Roster CSV
      </label>
      <textarea
        id="roster-csv"
        aria-label="Roster CSV"
        value={csvText}
        onChange={(event) => setCsvText(event.target.value)}
        className="mt-2 min-h-32 w-full rounded-md border border-slate-300 bg-white p-3 font-mono text-sm"
      />
      <button
        data-testid="import-roster"
        type="button"
        onClick={importRoster}
        disabled={isBusy}
        className="mt-3 rounded-md bg-slate-900 px-4 py-2 text-sm font-medium text-white disabled:opacity-50"
      >
        Import roster
      </button>

      {errors.length > 0 && (
        <div data-testid="import-error" role="alert" className="mt-4 text-sm text-red-700">
          {errors.join("; ")}
        </div>
      )}
      {rows.length > 0 && errors.length === 0 && (
        <div data-testid="import-success" className="mt-4 text-sm text-green-700">
          {rows.length} student{rows.length === 1 ? "" : "s"} ready to publish.
          <button
            data-testid="publish-roster"
            type="button"
            onClick={publish}
            disabled={isBusy}
            className="ml-3 font-semibold underline disabled:opacity-50"
          >
            Publish preview
          </button>
        </div>
      )}
      {publishedCount !== null && (
        <p data-testid="publish-result" className="mt-3 text-sm text-slate-700">
          Published {publishedCount} comparison{publishedCount === 1 ? "" : "s"}.
        </p>
      )}
    </section>
  );
}
