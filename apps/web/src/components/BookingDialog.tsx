interface BookingDialogProps {
  open: boolean;
  onClose: () => void;
}

export function BookingDialog({ open, onClose }: BookingDialogProps) {
  if (!open) {
    return null;
  }

  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/60">
      <div className="w-full max-w-md rounded-2xl border border-slate-800 bg-slate-900 p-6">
        <div className="flex items-center justify-between">
          <h3 className="text-lg font-semibold">Book a viewing</h3>
          <button className="text-sm text-slate-400 hover:text-white" onClick={onClose}>
            Close
          </button>
        </div>
        <p className="mt-2 text-sm text-slate-400">
          Available slots will appear here once the agent fetches them.
        </p>
        {/* TODO: Render slot picker */}
      </div>
    </div>
  );
}
