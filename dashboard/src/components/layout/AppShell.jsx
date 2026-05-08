import { Outlet } from "react-router-dom";
import Sidebar from "./Sidebar";

export default function AppShell() {
  return (
    <div className="flex h-screen w-full bg-bg-primary text-text-primary overflow-hidden">
      <Sidebar />
      <main className="flex-1 overflow-y-auto bg-bg-primary">
        <div className="h-full px-6 py-6 max-w-7xl mx-auto">
          <Outlet />
        </div>
      </main>
    </div>
  );
}
