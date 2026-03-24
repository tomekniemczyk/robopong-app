"use client";

import { Header } from "@/components/header";
import { DesktopSidebar, MobileBottomNav } from "@/components/navigation";
import { useApp } from "@/lib/store";
import { ConnectTab } from "@/components/tabs/connect-tab";
import { CalibrationTab } from "@/components/tabs/calibration-tab";
import { DrillsTab } from "@/components/tabs/drills-tab";
import { TrainingTab } from "@/components/tabs/training-tab";
import { ExercisesTab } from "@/components/tabs/exercises-tab";
import { CameraTab } from "@/components/tabs/camera-tab";
import { LogsTab } from "@/components/tabs/logs-tab";

export default function Home() {
  const { activeTab } = useApp();

  return (
    <div className="flex min-h-screen flex-col bg-background">
      <Header />
      <div className="flex flex-1">
        <DesktopSidebar />
        <main className="flex-1 overflow-auto pb-20 lg:pb-0">
          <div className="mx-auto max-w-6xl p-4">
            {activeTab === "connect" && <ConnectTab />}
            {activeTab === "calibration" && <CalibrationTab />}
            {activeTab === "drills" && <DrillsTab />}
            {activeTab === "training" && <TrainingTab />}
            {activeTab === "exercises" && <ExercisesTab />}
            {activeTab === "camera" && <CameraTab />}
            {activeTab === "logs" && <LogsTab />}
          </div>
        </main>
      </div>
      <MobileBottomNav />
    </div>
  );
}
