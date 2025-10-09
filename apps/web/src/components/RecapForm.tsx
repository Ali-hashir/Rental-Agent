import { ChangeEvent, FormEvent, useState } from "react";

export function RecapForm() {
  const [channel, setChannel] = useState<"sms" | "email">("email");
  const [value, setValue] = useState("");
  const [status, setStatus] = useState<string | null>(null);

  const handleSubmit = async (event: FormEvent<HTMLFormElement>) => {
    event.preventDefault();
    setStatus("Sending...");
    try {
      const resp = await fetch("/api/agent/tool/send_followup", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ lead_id: crypto.randomUUID(), channel })
      });
      if (!resp.ok) {
        throw new Error("Failed");
      }
      setStatus("Sent");
    } catch (error) {
      console.error(error);
      setStatus("Error");
    }
  };

  return (
    <form className="space-y-3" onSubmit={handleSubmit}>
      <div className="flex gap-3">
        <button
          type="button"
          className={`flex-1 rounded-full border px-4 py-2 text-sm ${channel === "email" ? "border-emerald-500 bg-emerald-500 text-black" : "border-slate-800 bg-slate-900"}`}
          onClick={() => setChannel("email")}
        >
          Email
        </button>
        <button
          type="button"
          className={`flex-1 rounded-full border px-4 py-2 text-sm ${channel === "sms" ? "border-emerald-500 bg-emerald-500 text-black" : "border-slate-800 bg-slate-900"}`}
          onClick={() => setChannel("sms")}
        >
          SMS
        </button>
      </div>
      <input
        className="w-full rounded-full border border-slate-800 bg-slate-950/50 px-4 py-2 text-sm text-slate-100"
        placeholder={channel === "sms" ? "Enter phone number" : "Enter email"}
        value={value}
  onChange={(event: ChangeEvent<HTMLInputElement>) => setValue(event.target.value)}
      />
      <button
        type="submit"
        className="w-full rounded-full bg-emerald-500 px-4 py-2 text-sm font-medium text-black transition hover:bg-emerald-400"
      >
        Send recap
      </button>
      {status && <p className="text-xs text-slate-400">{status}</p>}
    </form>
  );
}
