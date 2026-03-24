"use client";

import { useState } from "react";
import { useApp } from "@/lib/store";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Button } from "@/components/ui/button";
import { Badge } from "@/components/ui/badge";
import { Slider } from "@/components/ui/slider";
import { Input } from "@/components/ui/input";
import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from "@/components/ui/select";
import {
  Sheet,
  SheetContent,
  SheetHeader,
  SheetTitle,
  SheetTrigger,
} from "@/components/ui/sheet";
import {
  Dialog,
  DialogContent,
  DialogDescription,
  DialogFooter,
  DialogHeader,
  DialogTitle,
} from "@/components/ui/dialog";
import {
  Play,
  Square,
  RotateCcw,
  ChevronLeft,
  ChevronRight,
  Star,
  Download,
  Upload,
  Trash2,
  Save,
  AlertCircle,
  ArrowUp,
  ArrowDown,
} from "lucide-react";

export function CalibrationTab() {
  const {
    calibration,
    setCalibration,
    resetCalibration,
    presets,
    selectedPreset,
    setSelectedPreset,
    hasUnsavedChanges,
    t,
  } = useApp();

  const [showPresetsPanel, setShowPresetsPanel] = useState(false);
  const [showSaveDialog, setShowSaveDialog] = useState(false);
  const [newPresetName, setNewPresetName] = useState("");
  const [showDiagram, setShowDiagram] = useState<string | null>(null);

  const handleSliderChange = (field: keyof typeof calibration, value: number[]) => {
    setCalibration({ [field]: value[0] });
  };

  const handleStepChange = (field: keyof typeof calibration, delta: number) => {
    setCalibration({ [field]: calibration[field] + delta });
  };

  const handleSend = () => {
    console.log("[v0] Sending calibration:", calibration);
    // TODO: Send to robot
  };

  const handleThrow = () => {
    console.log("[v0] Throwing ball");
    // TODO: Send throw command
  };

  const handleStop = () => {
    console.log("[v0] Stopping motors");
    // TODO: Send stop command
  };

  return (
    <div className="space-y-6">
      <div className="flex items-center justify-between">
        <h2 className="text-xl font-semibold">{t("nav.calibration")}</h2>
        {hasUnsavedChanges && (
          <Badge variant="warning" className="gap-1">
            <AlertCircle className="h-3 w-3" />
            {t("cal.unsaved")}
          </Badge>
        )}
      </div>

      <div className="grid gap-6 lg:grid-cols-2">
        {/* Head Position Card */}
        <Card>
          <CardHeader>
            <CardTitle className="text-base">{t("cal.head_position")}</CardTitle>
          </CardHeader>
          <CardContent className="space-y-6">
            {/* Oscillation */}
            <SliderControl
              label={t("cal.oscillation")}
              value={calibration.oscillation}
              min={127}
              max={173}
              center={150}
              onChange={(v) => handleSliderChange("oscillation", v)}
              onStep={(d) => handleStepChange("oscillation", d)}
              hint="127 left - 150 center - 173 right"
              diagram="oscillation"
              onShowDiagram={setShowDiagram}
            />

            {/* Height */}
            <SliderControl
              label={t("cal.height")}
              value={calibration.height}
              min={75}
              max={210}
              center={150}
              onChange={(v) => handleSliderChange("height", v)}
              onStep={(d) => handleStepChange("height", d)}
              hint="75 low - 210 high"
              diagram="height"
              onShowDiagram={setShowDiagram}
            />

            {/* Rotation */}
            <SliderControl
              label={t("cal.rotation")}
              value={calibration.rotation}
              min={90}
              max={210}
              center={150}
              onChange={(v) => handleSliderChange("rotation", v)}
              onStep={(d) => handleStepChange("rotation", d)}
              hint="90 left - 150 center - 210 right"
              diagram="rotation"
              onShowDiagram={setShowDiagram}
            />
          </CardContent>
        </Card>

        {/* Motors Card */}
        <Card>
          <CardHeader>
            <CardTitle className="text-base">{t("cal.motors")}</CardTitle>
          </CardHeader>
          <CardContent className="space-y-6">
            {/* Top Motor */}
            <MotorControl
              label={t("cal.top_motor")}
              value={calibration.topSpeed}
              onChange={(v) => handleSliderChange("topSpeed", v)}
              onStep={(d) => handleStepChange("topSpeed", d)}
            />

            {/* Bottom Motor */}
            <MotorControl
              label={t("cal.bottom_motor")}
              value={calibration.bottomSpeed}
              onChange={(v) => handleSliderChange("bottomSpeed", v)}
              onStep={(d) => handleStepChange("bottomSpeed", d)}
            />

            {/* Wait Time */}
            <div className="space-y-2">
              <div className="flex items-center justify-between">
                <label className="text-sm font-medium">{t("cal.wait_time")}</label>
                <span className="rounded bg-surface-2 px-2 py-0.5 font-mono text-sm">
                  {calibration.waitMs}ms
                </span>
              </div>
              <Slider
                value={[calibration.waitMs]}
                min={200}
                max={10000}
                step={100}
                onValueChange={(v) => handleSliderChange("waitMs", v)}
              />
              <p className="text-xs text-muted">200ms - 10000ms</p>
            </div>
          </CardContent>
        </Card>
      </div>

      {/* Action Bar */}
      <div className="flex flex-wrap items-center gap-3">
        <Button onClick={handleSend} className="gap-2">
          <Play className="h-4 w-4" />
          {t("cal.send")}
        </Button>
        <Button onClick={handleThrow} variant="success" className="gap-2">
          <ArrowUp className="h-4 w-4" />
          {t("cal.throw")}
        </Button>
        <Button onClick={handleStop} variant="destructive" className="gap-2">
          <Square className="h-4 w-4" />
          {t("cal.stop")}
        </Button>
        <Button onClick={resetCalibration} variant="ghost" className="gap-2">
          <RotateCcw className="h-4 w-4" />
          {t("cal.reset")}
        </Button>

        <div className="ml-auto">
          <Sheet open={showPresetsPanel} onOpenChange={setShowPresetsPanel}>
            <SheetTrigger asChild>
              <Button variant="outline">
                {t("cal.presets")}
              </Button>
            </SheetTrigger>
            <SheetContent>
              <SheetHeader>
                <SheetTitle>{t("cal.presets")}</SheetTitle>
              </SheetHeader>
              <PresetsPanel
                presets={presets}
                selectedPreset={selectedPreset}
                onSelect={setSelectedPreset}
                onSave={() => setShowSaveDialog(true)}
              />
            </SheetContent>
          </Sheet>
        </div>
      </div>

      {/* Save Preset Dialog */}
      <Dialog open={showSaveDialog} onOpenChange={setShowSaveDialog}>
        <DialogContent>
          <DialogHeader>
            <DialogTitle>{t("cal.save_new")}</DialogTitle>
            <DialogDescription>
              Enter a name for the new preset
            </DialogDescription>
          </DialogHeader>
          <Input
            value={newPresetName}
            onChange={(e) => setNewPresetName(e.target.value)}
            placeholder="Preset name"
          />
          <DialogFooter>
            <Button variant="outline" onClick={() => setShowSaveDialog(false)}>
              {t("common.cancel")}
            </Button>
            <Button onClick={() => {
              console.log("[v0] Saving preset:", newPresetName);
              setShowSaveDialog(false);
              setNewPresetName("");
            }}>
              <Save className="mr-2 h-4 w-4" />
              {t("common.save")}
            </Button>
          </DialogFooter>
        </DialogContent>
      </Dialog>

      {/* Diagram Modal */}
      <Dialog open={showDiagram !== null} onOpenChange={() => setShowDiagram(null)}>
        <DialogContent className="max-w-md">
          <DialogHeader>
            <DialogTitle className="capitalize">{showDiagram}</DialogTitle>
          </DialogHeader>
          <div className="flex aspect-video items-center justify-center rounded-lg bg-surface-2">
            <span className="text-muted">Diagram: {showDiagram}</span>
          </div>
        </DialogContent>
      </Dialog>
    </div>
  );
}

interface SliderControlProps {
  label: string;
  value: number;
  min: number;
  max: number;
  center?: number;
  hint?: string;
  diagram?: string;
  onChange: (value: number[]) => void;
  onStep: (delta: number) => void;
  onShowDiagram?: (diagram: string) => void;
}

function SliderControl({
  label,
  value,
  min,
  max,
  hint,
  diagram,
  onChange,
  onStep,
  onShowDiagram,
}: SliderControlProps) {
  return (
    <div className="space-y-2">
      <div className="flex items-center justify-between">
        <div className="flex items-center gap-2">
          <label className="text-sm font-medium">{label}</label>
          {diagram && onShowDiagram && (
            <button
              onClick={() => onShowDiagram(diagram)}
              className="rounded bg-surface-2 px-1.5 py-0.5 text-[10px] text-muted hover:text-foreground"
            >
              ?
            </button>
          )}
        </div>
        <span className="rounded bg-surface-2 px-2 py-0.5 font-mono text-sm">{value}</span>
      </div>
      <div className="flex items-center gap-2">
        <Button
          variant="outline"
          size="sm"
          className="h-8 w-8 p-0"
          onClick={() => onStep(-2)}
        >
          <ChevronLeft className="h-4 w-4" />
        </Button>
        <Slider
          value={[value]}
          min={min}
          max={max}
          step={1}
          onValueChange={onChange}
          className="flex-1"
        />
        <Button
          variant="outline"
          size="sm"
          className="h-8 w-8 p-0"
          onClick={() => onStep(2)}
        >
          <ChevronRight className="h-4 w-4" />
        </Button>
      </div>
      {hint && <p className="text-xs text-muted">{hint}</p>}
    </div>
  );
}

interface MotorControlProps {
  label: string;
  value: number;
  onChange: (value: number[]) => void;
  onStep: (delta: number) => void;
}

function MotorControl({ label, value, onChange, onStep }: MotorControlProps) {
  const direction = value > 0 ? "CW" : value < 0 ? "CCW" : "-";
  const DirectionIcon = value > 0 ? ArrowUp : ArrowDown;

  return (
    <div className="space-y-2">
      <div className="flex items-center justify-between">
        <label className="text-sm font-medium">{label}</label>
        <div className="flex items-center gap-2">
          <span className="rounded bg-surface-2 px-2 py-0.5 font-mono text-sm">{value}</span>
          <Badge variant={value === 0 ? "secondary" : "outline"} className="gap-1">
            {value !== 0 && <DirectionIcon className="h-3 w-3" />}
            {direction}
          </Badge>
        </div>
      </div>
      <div className="flex items-center gap-2">
        <Button
          variant="outline"
          size="sm"
          className="h-8 w-8 p-0"
          onClick={() => onStep(-2)}
        >
          <ChevronLeft className="h-4 w-4" />
        </Button>
        <Slider
          value={[value]}
          min={-249}
          max={249}
          step={1}
          onValueChange={onChange}
          className="flex-1"
        />
        <Button
          variant="outline"
          size="sm"
          className="h-8 w-8 p-0"
          onClick={() => onStep(2)}
        >
          <ChevronRight className="h-4 w-4" />
        </Button>
      </div>
    </div>
  );
}

interface PresetsPanelProps {
  presets: { id?: number; name: string; is_default: boolean }[];
  selectedPreset: number | null;
  onSelect: (id: number | null) => void;
  onSave: () => void;
}

function PresetsPanel({ presets, selectedPreset, onSelect, onSave }: PresetsPanelProps) {
  return (
    <div className="mt-6 space-y-4">
      <Select
        value={selectedPreset?.toString() || ""}
        onValueChange={(v) => onSelect(v ? parseInt(v) : null)}
      >
        <SelectTrigger>
          <SelectValue placeholder="Select preset" />
        </SelectTrigger>
        <SelectContent>
          {presets.map((preset) => (
            <SelectItem key={preset.id} value={preset.id?.toString() || ""}>
              <div className="flex items-center gap-2">
                {preset.is_default && <Star className="h-3 w-3 text-warning" />}
                {preset.name}
              </div>
            </SelectItem>
          ))}
        </SelectContent>
      </Select>

      <div className="grid grid-cols-2 gap-2">
        <Button variant="outline" size="sm" disabled={!selectedPreset}>
          Load
        </Button>
        <Button variant="outline" size="sm" onClick={onSave}>
          {<Save className="mr-1 h-3 w-3" />}
          Save as New
        </Button>
        <Button variant="outline" size="sm" disabled={!selectedPreset}>
          Overwrite
        </Button>
        <Button variant="outline" size="sm" disabled={!selectedPreset}>
          <Star className="mr-1 h-3 w-3" />
          Set Default
        </Button>
      </div>

      <Button variant="destructive" size="sm" className="w-full" disabled={!selectedPreset}>
        <Trash2 className="mr-2 h-3 w-3" />
        Delete
      </Button>

      <div className="border-t border-border pt-4">
        <div className="flex gap-2">
          <Button variant="outline" size="sm" className="flex-1">
            <Upload className="mr-1 h-3 w-3" />
            Import JSON
          </Button>
          <Button variant="outline" size="sm" className="flex-1">
            <Download className="mr-1 h-3 w-3" />
            Export JSON
          </Button>
        </div>
      </div>
    </div>
  );
}
