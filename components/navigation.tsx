"use client";

import { useApp } from "@/lib/store";
import { cn } from "@/lib/utils";
import type { TabType } from "@/lib/types";
import {
  Bluetooth,
  Target,
  Layers,
  Dumbbell,
  Activity,
  Camera,
  FileText,
} from "lucide-react";

const tabs: { id: TabType; icon: typeof Bluetooth; labelKey: string }[] = [
  { id: "connect", icon: Bluetooth, labelKey: "nav.connect" },
  { id: "calibration", icon: Target, labelKey: "nav.calibration" },
  { id: "drills", icon: Layers, labelKey: "nav.drills" },
  { id: "training", icon: Dumbbell, labelKey: "nav.training" },
  { id: "exercises", icon: Activity, labelKey: "nav.exercises" },
  { id: "camera", icon: Camera, labelKey: "nav.camera" },
  { id: "logs", icon: FileText, labelKey: "nav.logs" },
];

export function DesktopSidebar() {
  const { activeTab, setActiveTab, t } = useApp();

  return (
    <aside className="hidden lg:flex lg:w-56 lg:flex-col lg:border-r lg:border-border lg:bg-surface">
      <nav className="flex flex-1 flex-col gap-1 p-3">
        {tabs.map((tab) => {
          const Icon = tab.icon;
          const isActive = activeTab === tab.id;
          return (
            <button
              key={tab.id}
              onClick={() => setActiveTab(tab.id)}
              className={cn(
                "flex items-center gap-3 rounded-lg px-3 py-2.5 text-sm font-medium transition-colors",
                isActive
                  ? "bg-primary text-primary-foreground"
                  : "text-muted hover:bg-surface-2 hover:text-foreground"
              )}
            >
              <Icon className="h-4 w-4" />
              {t(tab.labelKey)}
            </button>
          );
        })}
      </nav>
    </aside>
  );
}

export function MobileBottomNav() {
  const { activeTab, setActiveTab, t } = useApp();

  return (
    <nav className="fixed inset-x-0 bottom-0 z-40 flex h-16 items-center justify-around border-t border-border bg-surface pb-safe lg:hidden">
      {tabs.map((tab) => {
        const Icon = tab.icon;
        const isActive = activeTab === tab.id;
        return (
          <button
            key={tab.id}
            onClick={() => setActiveTab(tab.id)}
            className={cn(
              "flex flex-col items-center gap-0.5 px-2 py-1 transition-colors",
              isActive ? "text-primary" : "text-muted"
            )}
          >
            <Icon className="h-5 w-5" />
            <span className="text-[10px] font-medium">{t(tab.labelKey)}</span>
          </button>
        );
      })}
    </nav>
  );
}
