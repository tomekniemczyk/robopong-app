"use client";

import { useState } from "react";
import { useApp } from "@/lib/store";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Button } from "@/components/ui/button";
import { Badge } from "@/components/ui/badge";
import { Tabs, TabsContent, TabsList, TabsTrigger } from "@/components/ui/tabs";
import { ScrollArea } from "@/components/ui/scroll-area";
import {
  Dialog,
  DialogContent,
  DialogHeader,
  DialogTitle,
} from "@/components/ui/dialog";
import { Trash2, Copy, ArrowRight, ArrowLeft, Zap } from "lucide-react";
import type { LogEntry, ServerLogEntry } from "@/lib/types";

// Sample logs
const sampleRobotLogs: LogEntry[] = [
  { timestamp: "14:32:05.123", direction: "sent", message: "CALIBRATE 150 120 150" },
  { timestamp: "14:32:05.156", direction: "received", message: "OK CALIBRATE" },
  { timestamp: "14:32:06.234", direction: "sent", message: "MOTOR 120 -30" },
  { timestamp: "14:32:06.267", direction: "received", message: "OK MOTOR" },
  { timestamp: "14:32:08.100", direction: "status", message: "Motors spinning up" },
  { timestamp: "14:32:10.500", direction: "sent", message: "THROW" },
  { timestamp: "14:32:10.534", direction: "received", message: "OK THROW" },
  { timestamp: "14:32:11.000", direction: "status", message: "Ball thrown" },
  { timestamp: "14:32:15.000", direction: "sent", message: "STOP" },
  { timestamp: "14:32:15.033", direction: "received", message: "OK STOP" },
];

const sampleServerLogs: ServerLogEntry[] = [
  { timestamp: "14:32:00.001", level: "INFO", logger: "websocket", message: "Client connected from 192.168.1.10" },
  { timestamp: "14:32:01.234", level: "DEBUG", logger: "robot", message: "Initializing BLE connection" },
  { timestamp: "14:32:03.456", level: "INFO", logger: "robot", message: "Connected to Robopong 3050XL" },
  { timestamp: "14:32:05.100", level: "DEBUG", logger: "calibration", message: "Sending calibration command" },
  { timestamp: "14:32:06.200", level: "DEBUG", logger: "motor", message: "Setting motor speeds: top=120, bottom=-30" },
  { timestamp: "14:32:08.000", level: "INFO", logger: "motor", message: "Motors started successfully" },
  { timestamp: "14:32:10.456", level: "INFO", logger: "drill", message: "Executing throw command" },
  { timestamp: "14:32:15.000", level: "WARNING", logger: "motor", message: "Emergency stop triggered" },
  { timestamp: "14:32:20.000", level: "ERROR", logger: "ble", message: "Connection timeout - retrying" },
];

const levelColors: Record<string, string> = {
  DEBUG: "text-muted",
  INFO: "text-success",
  WARNING: "text-warning",
  ERROR: "text-danger",
};

const levelFilters = ["DEBUG", "INFO", "WARNING", "ERROR"] as const;

export function LogsTab() {
  const { robotLogs, serverLogs, clearRobotLogs, clearServerLogs, t } = useApp();
  const [activeFilters, setActiveFilters] = useState<string[]>(["INFO", "WARNING", "ERROR"]);
  const [showDiagReport, setShowDiagReport] = useState(false);

  // Use sample data if no real logs
  const displayRobotLogs = robotLogs.length > 0 ? robotLogs : sampleRobotLogs;
  const displayServerLogs = serverLogs.length > 0 ? serverLogs : sampleServerLogs;

  const filteredServerLogs = displayServerLogs.filter((log) => activeFilters.includes(log.level));

  const toggleFilter = (level: string) => {
    setActiveFilters((prev) =>
      prev.includes(level) ? prev.filter((l) => l !== level) : [...prev, level]
    );
  };

  const generateDiagReport = () => {
    const report = {
      timestamp: new Date().toISOString(),
      device: {
        name: "Robopong 3050XL",
        firmware: "v3.2.1",
        connection: "BLE",
      },
      robotLogs: displayRobotLogs.slice(-50),
      serverLogs: displayServerLogs.slice(-50),
    };
    return JSON.stringify(report, null, 2);
  };

  const copyDiagReport = async () => {
    await navigator.clipboard.writeText(generateDiagReport());
  };

  return (
    <div className="space-y-4">
      <div className="flex items-center justify-between">
        <h2 className="text-xl font-semibold">{t("nav.logs")}</h2>
        <Button variant="outline" onClick={() => setShowDiagReport(true)}>
          <Copy className="mr-2 h-4 w-4" />
          {t("logs.copy_report")}
        </Button>
      </div>

      <Tabs defaultValue="robot">
        <TabsList>
          <TabsTrigger value="robot">{t("logs.robot")}</TabsTrigger>
          <TabsTrigger value="server">{t("logs.server")}</TabsTrigger>
        </TabsList>

        <TabsContent value="robot" className="mt-4">
          <Card>
            <CardHeader className="flex flex-row items-center justify-between py-3">
              <CardTitle className="text-sm font-medium text-muted">
                {t("logs.robot")} ({displayRobotLogs.length} entries)
              </CardTitle>
              <Button size="sm" variant="ghost" onClick={clearRobotLogs}>
                <Trash2 className="mr-1 h-3 w-3" />
                {t("logs.clear")}
              </Button>
            </CardHeader>
            <CardContent className="p-0">
              <ScrollArea className="h-[500px]">
                <div className="font-mono text-xs">
                  {displayRobotLogs.map((log, i) => (
                    <RobotLogLine key={i} log={log} />
                  ))}
                </div>
              </ScrollArea>
            </CardContent>
          </Card>
        </TabsContent>

        <TabsContent value="server" className="mt-4">
          <Card>
            <CardHeader className="flex flex-row items-center justify-between py-3">
              <div className="flex items-center gap-4">
                <CardTitle className="text-sm font-medium text-muted">
                  {t("logs.server")} ({filteredServerLogs.length} entries)
                </CardTitle>
                <div className="flex gap-1">
                  {levelFilters.map((level) => (
                    <Badge
                      key={level}
                      variant={activeFilters.includes(level) ? "default" : "outline"}
                      className={`cursor-pointer text-[10px] ${
                        activeFilters.includes(level) ? "" : "opacity-50"
                      }`}
                      onClick={() => toggleFilter(level)}
                    >
                      {level}
                    </Badge>
                  ))}
                </div>
              </div>
              <Button size="sm" variant="ghost" onClick={clearServerLogs}>
                <Trash2 className="mr-1 h-3 w-3" />
                {t("logs.clear")}
              </Button>
            </CardHeader>
            <CardContent className="p-0">
              <ScrollArea className="h-[500px]">
                <div className="font-mono text-xs">
                  {filteredServerLogs.map((log, i) => (
                    <ServerLogLine key={i} log={log} />
                  ))}
                </div>
              </ScrollArea>
            </CardContent>
          </Card>
        </TabsContent>
      </Tabs>

      {/* Diagnostic Report Dialog */}
      <Dialog open={showDiagReport} onOpenChange={setShowDiagReport}>
        <DialogContent className="max-w-2xl">
          <DialogHeader>
            <DialogTitle>{t("logs.copy_report")}</DialogTitle>
          </DialogHeader>
          <textarea
            readOnly
            value={generateDiagReport()}
            className="h-80 w-full rounded-lg border border-border bg-background p-3 font-mono text-xs"
            onClick={(e) => (e.target as HTMLTextAreaElement).select()}
          />
          <div className="flex justify-end gap-2">
            <Button variant="outline" onClick={() => setShowDiagReport(false)}>
              {t("common.close")}
            </Button>
            <Button onClick={copyDiagReport}>
              <Copy className="mr-2 h-4 w-4" />
              Copy
            </Button>
          </div>
        </DialogContent>
      </Dialog>
    </div>
  );
}

function RobotLogLine({ log }: { log: LogEntry }) {
  const directionConfig = {
    sent: { icon: ArrowRight, color: "text-primary", label: "TX" },
    received: { icon: ArrowLeft, color: "text-success", label: "RX" },
    status: { icon: Zap, color: "text-warning", label: "ST" },
  };

  const config = directionConfig[log.direction];
  const Icon = config.icon;

  return (
    <div className="flex items-start gap-2 border-b border-border/50 px-4 py-2 hover:bg-surface-2">
      <span className="text-muted-foreground w-20 shrink-0">{log.timestamp}</span>
      <span className={`flex w-8 items-center gap-1 ${config.color}`}>
        <Icon className="h-3 w-3" />
      </span>
      <span className="flex-1 break-all">{log.message}</span>
    </div>
  );
}

function ServerLogLine({ log }: { log: ServerLogEntry }) {
  return (
    <div className="flex items-start gap-2 border-b border-border/50 px-4 py-2 hover:bg-surface-2">
      <span className="text-muted-foreground w-24 shrink-0">{log.timestamp}</span>
      <span className={`w-16 shrink-0 font-bold ${levelColors[log.level]}`}>{log.level}</span>
      <span className="text-primary w-24 shrink-0 truncate">{log.logger}</span>
      <span className="flex-1 break-all">{log.message}</span>
    </div>
  );
}
