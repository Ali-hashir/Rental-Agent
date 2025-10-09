import { Navigate, Route, Routes } from "react-router-dom";
import { MainLayout } from "./layouts/MainLayout";
import { CallPanel } from "./views/CallPanel";
import { AdminDashboard } from "./views/AdminDashboard";

export default function App() {
  return (
    <MainLayout>
      <Routes>
        <Route path="/" element={<CallPanel />} />
        <Route path="/admin" element={<AdminDashboard />} />
        <Route path="*" element={<Navigate to="/" replace />} />
      </Routes>
    </MainLayout>
  );
}
