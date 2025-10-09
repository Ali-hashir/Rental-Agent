interface ResultsPanelProps {
  onBook: () => void;
}

export function ResultsPanel({ onBook }: ResultsPanelProps) {
  // TODO: Render actual search results from agent results store.
  return (
    <div className="rounded-2xl border border-slate-800 bg-slate-900/60 p-6">
      <h2 className="text-lg font-semibold">Results</h2>
      <p className="mt-2 text-sm text-slate-400">
        Listings will appear here when the agent shares results.
      </p>
      <button
        className="mt-4 w-full rounded-full bg-emerald-500 px-4 py-2 text-sm font-medium text-black transition hover:bg-emerald-400"
        onClick={onBook}
      >
        Book viewing
      </button>
    </div>
  );
}
