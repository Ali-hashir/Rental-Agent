interface TranscriptPanelProps {
  sessionId: string | null;
}

export function TranscriptPanel({ sessionId }: TranscriptPanelProps) {
  // TODO: Subscribe to WebSocket captions stream for sessionId, show partial/final captions.
  return (
    <div className="h-48 overflow-y-auto space-y-2 text-sm text-slate-200">
      {sessionId ? (
        <p className="italic text-slate-400">Waiting for audio...</p>
      ) : (
        <p className="italic text-slate-500">Start a call to see captions.</p>
      )}
    </div>
  );
}
