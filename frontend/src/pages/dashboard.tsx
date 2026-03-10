import { useState, useCallback } from "react";
import { TopNav } from "@/components/dashboard/top-nav";
import { VorstandView } from "@/components/dashboard/vorstand-view";
import { SchatzmeisterView } from "@/components/dashboard/schatzmeister-view";
import { SpartenleiterView } from "@/components/dashboard/spartenleiter-view";
import type { DashboardView } from "@/types/dashboard";

export function DashboardPage() {
  const [activeView, setActiveView] = useState<DashboardView>("vorstand");
  const [memberCount, setMemberCount] = useState(0);

  const handleMemberCountChange = useCallback((count: number) => {
    setMemberCount(count);
  }, []);

  return (
    <div
      className="dashboard-shell flex h-full flex-col overflow-hidden"
    >
      <TopNav
        activeView={activeView}
        onViewChange={setActiveView}
        memberCount={memberCount}
      />
      <div className="flex-1 overflow-auto bg-gray-50">
        {activeView === "vorstand" && (
          <VorstandView onMemberCountChange={handleMemberCountChange} />
        )}
        {activeView === "schatzmeister" && <SchatzmeisterView />}
        {activeView === "spartenleiter" && <SpartenleiterView />}
      </div>
    </div>
  );
}
