import { ReactNode } from "react";
import { NavLink } from "react-router-dom";

interface MainLayoutProps {
  children: ReactNode;
}

export function MainLayout({ children }: MainLayoutProps) {
  return (
    <div className="min-h-screen bg-slate-950 text-slate-100">
      <header className="border-b border-slate-800 bg-slate-900/80 backdrop-blur">
        <div className="mx-auto flex max-w-5xl items-center justify-between px-6 py-4">
          <div className="text-lg font-semibold">Rental Voice Receptionist</div>
          <nav className="flex gap-4 text-sm">
            <NavLink to="/" className={({ isActive }) => (isActive ? "text-white" : "text-slate-400 hover:text-white")}>Call</NavLink>
            <NavLink to="/admin" className={({ isActive }) => (isActive ? "text-white" : "text-slate-400 hover:text-white")}>Admin</NavLink>
          </nav>
        </div>
      </header>
      <main className="mx-auto max-w-5xl px-6 py-8">{children}</main>
    </div>
  );
}
