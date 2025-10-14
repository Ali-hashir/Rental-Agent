import { useEffect, useMemo, useState } from "react";
import { useMutation, useQuery } from "@tanstack/react-query";
import type { ListingCard, TimeSlot } from "../types";

interface BookingDialogProps {
  open: boolean;
  unit: ListingCard | null;
  onClose: () => void;
}

interface SlotsResponse {
  slots: TimeSlot[];
}

interface BookViewingResponse {
  appointment_id: string;
  calendar_event_url: string | null;
}

interface BookViewingPayload {
  unit_id: string;
  slot_start: string;
  visitor: {
    name: string;
    phone: string;
    email: string;
  };
}

const fetchSlots = async (unitId: string): Promise<TimeSlot[]> => {
  const response = await fetch("/api/agent/tool/list_slots", {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({
      unit_id: unitId,
      days_ahead: 14
    })
  });

  if (!response.ok) {
    throw new Error("Failed to load availability");
  }
  const data = (await response.json()) as SlotsResponse;
  return data.slots;
};

const bookViewing = async (payload: BookViewingPayload): Promise<BookViewingResponse> => {
  const response = await fetch("/api/agent/tool/book_viewing", {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify(payload)
  });

  if (!response.ok) {
    throw new Error("Unable to book this slot");
  }
  return (await response.json()) as BookViewingResponse;
};

const formatSlot = (slot: TimeSlot) => {
  const start = new Date(slot.start);
  const end = new Date(slot.end);
  const date = start.toLocaleDateString(undefined, { month: "short", day: "numeric" });
  const startTime = start.toLocaleTimeString([], { hour: "2-digit", minute: "2-digit" });
  const endTime = end.toLocaleTimeString([], { hour: "2-digit", minute: "2-digit" });
  return `${date} ${startTime} - ${endTime}`;
};

export function BookingDialog({ open, unit, onClose }: BookingDialogProps) {
  const [selectedSlot, setSelectedSlot] = useState<TimeSlot | null>(null);
  const [name, setName] = useState("");
  const [email, setEmail] = useState("");
  const [phone, setPhone] = useState("");

  const resetForm = () => {
    setSelectedSlot(null);
    setName("");
    setEmail("");
    setPhone("");
  };

  useEffect(() => {
    if (!open) {
      resetForm();
    }
  }, [open]);

  const {
    data: slots,
    isLoading,
    isError,
    refetch
  } = useQuery({
    queryKey: ["slots", unit?.unitId],
    queryFn: () => fetchSlots(unit!.unitId),
    enabled: open && !!unit,
    staleTime: 60 * 1000
  });

  const bookMutation = useMutation({
    mutationFn: () =>
      bookViewing({
        unit_id: unit!.unitId,
        slot_start: selectedSlot!.start,
        visitor: { name, email, phone }
      }),
    onSuccess: () => {
      resetForm();
      onClose();
    }
  });

  const { isPending, isError: isBookingError } = bookMutation;

  const disableSubmit = useMemo(() => {
    if (!selectedSlot) {
      return true;
    }
    if (!name.trim() || !email.trim()) {
      return true;
    }
    return isPending;
  }, [selectedSlot, name, email, isPending]);

  if (!open || !unit) {
    return null;
  }

  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/60 px-4">
      <div className="w-full max-w-lg rounded-2xl border border-slate-800 bg-slate-900 p-6 shadow-xl">
        <div className="flex items-center justify-between gap-4">
          <div>
            <h3 className="text-lg font-semibold text-white">Book a viewing</h3>
            <p className="text-xs text-slate-400">
              {unit.title} - {unit.propertyName}
            </p>
          </div>
          <button className="text-sm text-slate-400 transition hover:text-white" onClick={onClose}>
            Close
          </button>
        </div>

        <section className="mt-4 space-y-3">
          <header className="flex items-center justify-between">
            <h4 className="text-sm font-semibold text-slate-200">Available slots</h4>
            <button
              type="button"
              onClick={() => unit && refetch()}
              className="rounded-full border border-slate-700 px-3 py-1 text-xs text-slate-300 transition hover:border-slate-500"
            >
              Refresh
            </button>
          </header>

          {isLoading && <p className="text-xs text-slate-400">Fetching fresh availability...</p>}
          {isError && (
            <p className="text-xs text-rose-400">
              Availability lookup failed. Please refresh or try again later.
            </p>
          )}

          {!isLoading && !isError && slots && slots.length === 0 && (
            <p className="text-xs text-slate-400">
              No slots are currently available for this unit. Try another listing or extend the window.
            </p>
          )}

          <div className="grid gap-2 sm:grid-cols-2">
            {slots?.map((slot) => {
              const isActive = selectedSlot?.start === slot.start;
              return (
                <button
                  key={slot.start}
                  type="button"
                  onClick={() => setSelectedSlot(slot)}
                  className={`rounded-xl border px-3 py-2 text-left text-xs transition ${
                    isActive
                      ? "border-emerald-400 bg-emerald-500/10 text-emerald-300"
                      : "border-slate-800 bg-slate-950 text-slate-300 hover:border-slate-600"
                  }`}
                >
                  {formatSlot(slot)}
                </button>
              );
            })}
          </div>
        </section>

        <section className="mt-6 space-y-3">
          <h4 className="text-sm font-semibold text-slate-200">Visitor details</h4>
          <div className="grid gap-3">
            <input
              className="rounded-full border border-slate-800 bg-slate-950 px-4 py-2 text-sm text-slate-100 focus:border-emerald-500 focus:outline-none"
              placeholder="Full name"
              value={name}
              onChange={(event) => setName(event.target.value)}
            />
            <input
              className="rounded-full border border-slate-800 bg-slate-950 px-4 py-2 text-sm text-slate-100 focus:border-emerald-500 focus:outline-none"
              placeholder="Email address"
              type="email"
              value={email}
              onChange={(event) => setEmail(event.target.value)}
            />
            <input
              className="rounded-full border border-slate-800 bg-slate-950 px-4 py-2 text-sm text-slate-100 focus:border-emerald-500 focus:outline-none"
              placeholder="Phone number (optional)"
              value={phone}
              onChange={(event) => setPhone(event.target.value)}
            />
          </div>
        </section>

        {isBookingError && (
          <p className="mt-3 text-xs text-rose-400">We couldn&apos;t book this slot. Please pick another time.</p>
        )}

        <button
          type="button"
          className="mt-6 w-full rounded-full bg-emerald-500 px-4 py-2 text-sm font-medium text-black transition hover:bg-emerald-400 disabled:cursor-not-allowed disabled:bg-slate-700 disabled:text-slate-300"
          onClick={() => bookMutation.mutate()}
          disabled={disableSubmit}
        >
          {isPending ? "Booking..." : "Confirm booking"}
        </button>
      </div>
    </div>
  );
}
