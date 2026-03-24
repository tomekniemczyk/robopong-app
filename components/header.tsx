"use client";

import { useState } from "react";
import { useApp } from "@/lib/store";
import { Button } from "@/components/ui/button";
import { Badge } from "@/components/ui/badge";
import {
  Sheet,
  SheetContent,
  SheetHeader,
  SheetTitle,
  SheetTrigger,
} from "@/components/ui/sheet";
import { Info, Users } from "lucide-react";
import type { Language } from "@/lib/types";

const languageFlags: Record<Language, string> = {
  pl: "PL",
  en: "EN",
  de: "DE",
  fr: "FR",
  zh: "ZH",
};

export function Header() {
  const {
    connectionStatus,
    robotName,
    userRole,
    language,
    setLanguage,
    sessions,
    sessionId,
    t,
  } = useApp();
  const [showDeviceInfo, setShowDeviceInfo] = useState(false);
  const [showSessions, setShowSessions] = useState(false);

  const statusColor = {
    connected: "bg-success",
    disconnected: "bg-muted-foreground",
    simulation: "bg-warning",
  }[connectionStatus];

  const roleVariant = {
    controller: "success" as const,
    observer: "secondary" as const,
    pending: "warning" as const,
  }[userRole];

  const roleIcon = {
    controller: "C",
    observer: "O",
    pending: "P",
  }[userRole];

  return (
    <header className="sticky top-0 z-40 flex h-14 items-center justify-between border-b border-border bg-surface px-4">
      <div className="flex items-center gap-3">
        <h1 className="text-lg font-bold tracking-tight">AcePad</h1>
        <div className="flex items-center gap-2">
          <span className={`h-2 w-2 rounded-full ${statusColor}`} />
          <span className="text-sm text-muted">{robotName}</span>
        </div>
      </div>

      <div className="flex items-center gap-2">
        {/* Role badge */}
        <Badge variant={roleVariant} className="gap-1">
          <span className="font-mono text-[10px]">{roleIcon}</span>
          {t(`role.${userRole}`)}
        </Badge>

        {/* Language selector */}
        <div className="flex items-center gap-0.5 rounded-md border border-border p-0.5">
          {(Object.keys(languageFlags) as Language[]).map((lang) => (
            <button
              key={lang}
              onClick={() => setLanguage(lang)}
              className={`rounded px-1.5 py-0.5 text-[10px] font-bold transition-colors ${
                language === lang
                  ? "bg-primary text-primary-foreground"
                  : "text-muted hover:text-foreground"
              }`}
            >
              {languageFlags[lang]}
            </button>
          ))}
        </div>

        {/* Device info button */}
        <Sheet open={showDeviceInfo} onOpenChange={setShowDeviceInfo}>
          <SheetTrigger asChild>
            <Button variant="ghost" size="icon" className="h-8 w-8">
              <Info className="h-4 w-4" />
            </Button>
          </SheetTrigger>
          <SheetContent>
            <SheetHeader>
              <SheetTitle>{t("device.info")}</SheetTitle>
            </SheetHeader>
            <DeviceInfoContent />
          </SheetContent>
        </Sheet>

        {/* Sessions button */}
        <Sheet open={showSessions} onOpenChange={setShowSessions}>
          <SheetTrigger asChild>
            <Button variant="outline" size="sm" className="gap-1.5 text-xs">
              <Users className="h-3.5 w-3.5" />
              {sessions.length || 1}
            </Button>
          </SheetTrigger>
          <SheetContent>
            <SheetHeader>
              <SheetTitle>{t("sessions.title")}</SheetTitle>
            </SheetHeader>
            <SessionsContent
              sessions={sessions}
              currentSessionId={sessionId}
              userRole={userRole}
              t={t}
            />
          </SheetContent>
        </Sheet>
      </div>
    </header>
  );
}

function DeviceInfoContent() {
  const { robotName, transport, lastAddr, firmware, connectionStatus, t } = useApp();

  const items = [
    { label: t("device.name"), value: robotName },
    { label: t("device.transport"), value: transport?.toUpperCase() || "-" },
    { label: transport === "ble" ? t("device.mac") : t("device.port"), value: lastAddr || "-" },
    { label: t("connect.firmware"), value: firmware || "-" },
    {
      label: t("status.connected"),
      value: connectionStatus === "connected" ? t("connect.calibrated") : t("connect.not_calibrated"),
    },
  ];

  return (
    <div className="mt-6 space-y-4">
      {items.map((item) => (
        <div key={item.label} className="flex items-center justify-between border-b border-border pb-3">
          <span className="text-xs font-medium uppercase tracking-wider text-muted">{item.label}</span>
          <span className="text-sm font-medium">{item.value}</span>
        </div>
      ))}
    </div>
  );
}

interface SessionsContentProps {
  sessions: { id: string; role: string; ip?: string; since: string }[];
  currentSessionId: string;
  userRole: string;
  t: (key: string) => string;
}

function SessionsContent({ sessions, currentSessionId, userRole, t }: SessionsContentProps) {
  const mockSessions = sessions.length
    ? sessions
    : [
        { id: currentSessionId, role: userRole, ip: "192.168.1.10", since: new Date().toISOString() },
      ];

  return (
    <div className="mt-6 space-y-3">
      {mockSessions.map((session) => (
        <div
          key={session.id}
          className="flex items-center justify-between rounded-lg border border-border bg-surface-2 p-3"
        >
          <div className="flex flex-col gap-1">
            <div className="flex items-center gap-2">
              <Badge variant={session.role === "controller" ? "success" : "secondary"} className="text-[10px]">
                {t(`role.${session.role}`)}
              </Badge>
              {session.id === currentSessionId && (
                <span className="text-xs text-primary">You</span>
              )}
            </div>
            <span className="font-mono text-xs text-muted">{session.id}</span>
            {session.ip && <span className="text-xs text-muted">{session.ip}</span>}
          </div>
        </div>
      ))}

      {userRole === "controller" && (
        <Button variant="outline" className="mt-4 w-full">
          {t("sessions.release")}
        </Button>
      )}
      {userRole === "observer" && (
        <Button className="mt-4 w-full">
          {t("sessions.takeover")}
        </Button>
      )}
    </div>
  );
}
