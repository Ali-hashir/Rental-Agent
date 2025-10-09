export function AdminDashboard() {
  return (
    <div className="space-y-6">
      <header>
        <h1 className="text-2xl font-semibold">Admin dashboard</h1>
        <p className="text-sm text-slate-400">
          Review calls, leads, and appointments once the API is connected.
        </p>
      </header>
      <section className="rounded-2xl border border-slate-800 bg-slate-900/60 p-6">
        <h2 className="text-lg font-semibold">Calls</h2>
        <p className="mt-2 text-sm text-slate-400">Implement call listing table.</p>
      </section>
      <section className="rounded-2xl border border-slate-800 bg-slate-900/60 p-6">
        <h2 className="text-lg font-semibold">Leads</h2>
        <p className="mt-2 text-sm text-slate-400">Implement lead summary and filters.</p>
      </section>
      <section className="rounded-2xl border border-slate-800 bg-slate-900/60 p-6">
        <h2 className="text-lg font-semibold">Appointments</h2>
        <p className="mt-2 text-sm text-slate-400">Implement booking calendar view.</p>
      </section>
    </div>
  );
}
