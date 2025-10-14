import { useState } from "react";
import { useMutation } from "@tanstack/react-query";
import { clsx } from "clsx";
import { useRtcClient } from "../webrtc/useRtcClient";
import { TranscriptPanel } from "../components/TranscriptPanel";
import { ResultsPanel } from "../components/ResultsPanel";
import { BookingDialog } from "../components/BookingDialog";
import { VuMeter } from "../components/VuMeter";
import { RecapForm } from "../components/RecapForm";
import type { ListingCard } from "../types";

export function CallPanel() {
  const [sessionId, setSessionId] = useState<string | null>(null);
  const [showBooking, setShowBooking] = useState(false);
  const [selectedListing, setSelectedListing] = useState<ListingCard | null>(null);
  const [inputLevel, setInputLevel] = useState(0);
  const rtc = useRtcClient({ onLevel: setInputLevel });

  const startCall = useMutation({
    mutationFn: async () => {
      const resp = await fetch("/api/rtc/token", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ room: "public", user_id: crypto.randomUUID() })
      });
      if (!resp.ok) {
        throw new Error("Failed to start call");
      }
      const data = (await resp.json()) as { token: string; expires_in: number };
      const newSessionId = crypto.randomUUID();
      setSessionId(newSessionId);
      await rtc.connect({ token: data.token, sessionId: newSessionId });
    }
  });

  const stopCall = async () => {
    rtc.disconnect();
    setSessionId(null);
  };

  const handleBook = (listing: ListingCard) => {
    setSelectedListing(listing);
    setShowBooking(true);
  };

  const closeBooking = () => {
    setShowBooking(false);
    setSelectedListing(null);
  };

  return (
    <div className="grid gap-6 lg:grid-cols-[2fr_1fr]">
      <section className="rounded-2xl border border-slate-800 bg-slate-900/60 p-6">
        <div className="flex items-center justify-between">
          <h2 className="text-xl font-semibold">Call</h2>
          <div className="flex gap-3">
            <button
              className={clsx(
                "rounded-full px-4 py-2 text-sm font-medium transition",
                startCall.isPending ? "bg-slate-600" : "bg-emerald-500 text-black hover:bg-emerald-400"
              )}
              onClick={() => startCall.mutate()}
              disabled={startCall.isPending}
            >
              {sessionId ? "Reconnect" : "Call"}
            </button>
            <button
              className="rounded-full bg-rose-500 px-4 py-2 text-sm font-medium text-black transition hover:bg-rose-400"
              onClick={stopCall}
            >
              Stop
            </button>
          </div>
        </div>
        <div className="mt-4 grid gap-4">
          <div className="rounded-xl border border-slate-800 bg-slate-950/50 p-4">
            <p className="text-sm text-slate-400">Mic level</p>
            <VuMeter level={inputLevel} />
          </div>
          <div className="rounded-xl border border-slate-800 bg-slate-950/50 p-4">
            <p className="text-sm text-slate-400">Live captions</p>
            <TranscriptPanel sessionId={sessionId} />
          </div>
          <div className="rounded-xl border border-slate-800 bg-slate-950/50 p-4">
            <p className="text-sm text-slate-400">Agent responses</p>
            {/* TODO: Render TTS status / progress */}
          </div>
        </div>
      </section>
      <aside className="space-y-6">
        <ResultsPanel onBook={handleBook} />
        <div className="rounded-2xl border border-slate-800 bg-slate-900/60 p-6">
          <h2 className="text-lg font-semibold">Send recap</h2>
          <p className="mt-1 text-sm text-slate-400">Follow up with the visitor via SMS or email.</p>
          <div className="mt-4">
            <RecapForm />
          </div>
        </div>
      </aside>
      <BookingDialog open={showBooking} unit={selectedListing} onClose={closeBooking} />
    </div>
  );
}
