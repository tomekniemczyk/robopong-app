"use client";

import { useState, useEffect } from "react";
import { useApp } from "@/lib/store";
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "@/components/ui/card";
import { Button } from "@/components/ui/button";
import { Badge } from "@/components/ui/badge";
import { Progress } from "@/components/ui/progress";
import { Switch } from "@/components/ui/switch";
import { Bluetooth, Usb, RefreshCw, Wifi, WifiOff, CheckCircle, AlertCircle } from "lucide-react";

interface BLEDevice {
  name: string;
  address: string;
  rssi: number;
}

interface USBPort {
  port: string;
  description: string;
}

export function ConnectTab() {
  const {
    connectionStatus,
    robotName,
    transport,
    lastAddr,
    firmware,
    simulationMode,
    setConnectionStatus,
    setSimulationMode,
    setActiveTab,
    t,
  } = useApp();

  const [bleScanning, setBleScanning] = useState(false);
  const [bleScanProgress, setBleScanProgress] = useState(0);
  const [bleDevices, setBleDevices] = useState<BLEDevice[]>([]);
  const [usbScanning, setUsbScanning] = useState(false);
  const [usbPorts, setUsbPorts] = useState<USBPort[]>([]);

  // Simulated BLE scan
  const startBleScan = () => {
    setBleScanning(true);
    setBleScanProgress(0);
    setBleDevices([]);

    const interval = setInterval(() => {
      setBleScanProgress((prev) => {
        if (prev >= 100) {
          clearInterval(interval);
          setBleScanning(false);
          // Mock devices
          setBleDevices([
            { name: "Robopong 3050XL", address: "AA:BB:CC:DD:EE:FF", rssi: -65 },
            { name: "Newgy 2050", address: "11:22:33:44:55:66", rssi: -72 },
          ]);
          return 100;
        }
        return prev + 12.5;
      });
    }, 1000);
  };

  // Simulated USB scan
  const startUsbScan = () => {
    setUsbScanning(true);
    setUsbPorts([]);

    setTimeout(() => {
      setUsbScanning(false);
      setUsbPorts([
        { port: "/dev/ttyUSB0", description: "FTDI FT232R" },
        { port: "/dev/ttyUSB1", description: "CH340" },
      ]);
    }, 1500);
  };

  const connectToDevice = (type: "ble" | "usb", address: string) => {
    // Simulate connection
    setConnectionStatus("connected");
  };

  const disconnect = () => {
    setConnectionStatus("disconnected");
  };

  const isConnected = connectionStatus === "connected" || connectionStatus === "simulation";

  // Connected device view
  if (isConnected) {
    return (
      <div className="space-y-6">
        <Card>
          <CardHeader>
            <div className="flex items-center justify-between">
              <div className="flex items-center gap-3">
                <div className="flex h-10 w-10 items-center justify-center rounded-full bg-success/20">
                  <CheckCircle className="h-5 w-5 text-success" />
                </div>
                <div>
                  <CardTitle className="text-lg">{robotName}</CardTitle>
                  <CardDescription className="flex items-center gap-2">
                    <Badge variant={simulationMode ? "warning" : "success"}>
                      {transport?.toUpperCase() || "SIM"}
                    </Badge>
                    {lastAddr || t("status.simulation")}
                  </CardDescription>
                </div>
              </div>
            </div>
          </CardHeader>
          <CardContent className="space-y-4">
            <div className="grid gap-3">
              <div className="flex items-center justify-between rounded-lg border border-border p-3">
                <span className="text-sm text-muted">{t("connect.firmware")}</span>
                <span className="font-mono text-sm">{firmware || "v3.2.1"}</span>
              </div>
              <div className="flex items-center justify-between rounded-lg border border-border p-3">
                <span className="text-sm text-muted">{t("nav.calibration")}</span>
                <div className="flex items-center gap-2">
                  {true ? (
                    <>
                      <CheckCircle className="h-4 w-4 text-success" />
                      <span className="text-sm text-success">{t("connect.calibrated")}</span>
                    </>
                  ) : (
                    <>
                      <AlertCircle className="h-4 w-4 text-warning" />
                      <Button
                        variant="link"
                        size="sm"
                        className="h-auto p-0 text-warning"
                        onClick={() => setActiveTab("calibration")}
                      >
                        {t("connect.not_calibrated")}
                      </Button>
                    </>
                  )}
                </div>
              </div>
            </div>

            <div className="flex gap-2 pt-2">
              <Button variant="destructive" className="flex-1" onClick={disconnect}>
                {t("connect.disconnect")}
              </Button>
              {transport === "ble" && (
                <Button variant="outline">
                  {t("connect.reset_ble")}
                </Button>
              )}
            </div>
          </CardContent>
        </Card>
      </div>
    );
  }

  // Disconnected view
  return (
    <div className="space-y-6">
      <div className="grid gap-6 md:grid-cols-2">
        {/* BLE Card */}
        <Card>
          <CardHeader>
            <div className="flex items-center gap-3">
              <div className="flex h-10 w-10 items-center justify-center rounded-full bg-primary/20">
                <Bluetooth className="h-5 w-5 text-primary" />
              </div>
              <div>
                <CardTitle>{t("connect.ble.title")}</CardTitle>
                <CardDescription>Wireless connection via Bluetooth LE</CardDescription>
              </div>
            </div>
          </CardHeader>
          <CardContent className="space-y-4">
            <Button
              className="w-full"
              onClick={startBleScan}
              disabled={bleScanning}
            >
              {bleScanning ? (
                <>
                  <RefreshCw className="mr-2 h-4 w-4 animate-spin" />
                  Scanning...
                </>
              ) : (
                <>
                  <Bluetooth className="mr-2 h-4 w-4" />
                  {t("connect.ble.scan")}
                </>
              )}
            </Button>

            {bleScanning && (
              <Progress value={bleScanProgress} className="h-2" />
            )}

            {bleDevices.length > 0 && (
              <div className="space-y-2">
                {bleDevices.map((device) => (
                  <div
                    key={device.address}
                    className="flex items-center justify-between rounded-lg border border-border p-3 transition-colors hover:bg-surface-2"
                  >
                    <div className="flex items-center gap-3">
                      <Wifi className="h-4 w-4 text-muted" />
                      <div>
                        <div className="text-sm font-medium">{device.name}</div>
                        <div className="font-mono text-xs text-muted">{device.address}</div>
                      </div>
                    </div>
                    <Button
                      size="sm"
                      onClick={() => connectToDevice("ble", device.address)}
                    >
                      {t("conn.connect")}
                    </Button>
                  </div>
                ))}
              </div>
            )}
          </CardContent>
        </Card>

        {/* USB Card */}
        <Card>
          <CardHeader>
            <div className="flex items-center gap-3">
              <div className="flex h-10 w-10 items-center justify-center rounded-full bg-primary/20">
                <Usb className="h-5 w-5 text-primary" />
              </div>
              <div>
                <CardTitle>{t("connect.usb.title")}</CardTitle>
                <CardDescription>Wired connection via USB cable</CardDescription>
              </div>
            </div>
          </CardHeader>
          <CardContent className="space-y-4">
            <Button
              className="w-full"
              onClick={startUsbScan}
              disabled={usbScanning}
            >
              {usbScanning ? (
                <>
                  <RefreshCw className="mr-2 h-4 w-4 animate-spin" />
                  Scanning...
                </>
              ) : (
                <>
                  <Usb className="mr-2 h-4 w-4" />
                  {t("connect.usb.scan")}
                </>
              )}
            </Button>

            {usbPorts.length > 0 && (
              <div className="space-y-2">
                {usbPorts.map((port) => (
                  <div
                    key={port.port}
                    className="flex items-center justify-between rounded-lg border border-border p-3 transition-colors hover:bg-surface-2"
                  >
                    <div>
                      <div className="font-mono text-sm font-medium">{port.port}</div>
                      <div className="text-xs text-muted">{port.description}</div>
                    </div>
                    <Button
                      size="sm"
                      onClick={() => connectToDevice("usb", port.port)}
                    >
                      {t("conn.connect")}
                    </Button>
                  </div>
                ))}
              </div>
            )}
          </CardContent>
        </Card>
      </div>

      {/* Bottom section */}
      <div className="flex flex-col gap-4 sm:flex-row sm:items-center sm:justify-between">
        <Button variant="ghost" disabled>
          <RefreshCw className="mr-2 h-4 w-4" />
          {t("connect.reconnect")}
        </Button>

        <div className="flex items-center gap-3 rounded-lg border border-border bg-surface p-3">
          <div className="flex-1">
            <div className="flex items-center gap-2">
              <span className="text-sm font-medium">{t("connect.simulation")}</span>
              {simulationMode && (
                <Badge variant="warning">Active</Badge>
              )}
            </div>
            <p className="text-xs text-muted">Test drills without robot hardware</p>
          </div>
          <Switch
            checked={simulationMode}
            onCheckedChange={setSimulationMode}
          />
        </div>
      </div>
    </div>
  );
}
