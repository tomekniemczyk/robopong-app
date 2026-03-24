"use client";

import { useApp } from "@/lib/store";
import { Card, CardContent } from "@/components/ui/card";
import { Camera } from "lucide-react";

export function CameraTab() {
  const { t } = useApp();
  const cameraUrl = null; // Would come from config/API

  return (
    <div className="space-y-4">
      <h2 className="text-xl font-semibold">{t("nav.camera")}</h2>

      <Card className="overflow-hidden">
        <CardContent className="p-0">
          {cameraUrl ? (
            <iframe
              src={cameraUrl}
              className="aspect-video w-full"
              allow="accelerometer; autoplay; clipboard-write; encrypted-media; gyroscope; picture-in-picture"
              allowFullScreen
            />
          ) : (
            <div className="flex aspect-video flex-col items-center justify-center gap-4 bg-surface-2">
              <div className="flex h-20 w-20 items-center justify-center rounded-full bg-muted/20">
                <Camera className="h-10 w-10 text-muted" />
              </div>
              <p className="text-lg text-muted">{t("camera.unavailable")}</p>
              <p className="max-w-md text-center text-sm text-muted">
                Configure a camera stream URL in the settings to view your robot's perspective here.
              </p>
            </div>
          )}
        </CardContent>
      </Card>
    </div>
  );
}
