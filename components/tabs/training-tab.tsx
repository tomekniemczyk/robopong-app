"use client";

import { useState } from "react";
import { useApp } from "@/lib/store";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Button } from "@/components/ui/button";
import { Badge } from "@/components/ui/badge";
import { Input } from "@/components/ui/input";
import { Progress } from "@/components/ui/progress";
import { Slider } from "@/components/ui/slider";
import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from "@/components/ui/select";
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
  Pause,
  Square,
  SkipForward,
  Pencil,
  Trash2,
  Plus,
  Clock,
  ChevronUp,
  ChevronDown,
  Dumbbell,
  Activity,
} from "lucide-react";
import type { Training, TrainingStep } from "@/lib/types";

// Sample trainings
const sampleTrainings: Training[] = [
  {
    id: 1,
    name: "Morning Warmup",
    description: "Quick warmup routine",
    countdown_sec: 15,
    steps: [
      { drill_id: 1, drill_name: "Forehand Warmup", count: 30, percent: 80, pause_after_sec: 15 },
      { drill_id: 2, drill_name: "Backhand Warmup", count: 30, percent: 80, pause_after_sec: 15 },
      { drill_id: 3, drill_name: "Forehand Topspin", count: 40, percent: 100, pause_after_sec: 30 },
    ],
  },
  {
    id: 2,
    name: "Footwork Intensive",
    description: "Focus on footwork patterns",
    countdown_sec: 20,
    steps: [
      { drill_id: 4, drill_name: "Side-to-Side", count: 50, percent: 90, pause_after_sec: 20 },
      { drill_id: 5, drill_name: "Falkenberg", count: 60, percent: 100, pause_after_sec: 30 },
      { drill_id: 6, drill_name: "Random Full Table", count: 60, percent: 110, pause_after_sec: 0 },
    ],
  },
];

const availableDrills = [
  { id: 1, name: "Forehand Warmup" },
  { id: 2, name: "Backhand Warmup" },
  { id: 3, name: "Forehand Topspin" },
  { id: 4, name: "Side-to-Side" },
  { id: 5, name: "Falkenberg" },
  { id: 6, name: "Random Full Table" },
];

export function TrainingTab() {
  const { activeTraining, setActiveTraining, t } = useApp();
  const [trainings, setTrainings] = useState<Training[]>(sampleTrainings);
  const [editingTraining, setEditingTraining] = useState<Training | null>(null);
  const [showDeleteConfirm, setShowDeleteConfirm] = useState<number | null>(null);

  const startTraining = (training: Training) => {
    const firstStep = training.steps[0];
    const totalBalls = training.steps.reduce((sum, step) => sum + step.count, 0);
    setActiveTraining({
      name: training.name,
      currentStep: 1,
      totalSteps: training.steps.length,
      stepName: firstStep.drill_name,
      currentBall: 0,
      totalBalls,
      phase: "COUNTDOWN",
      timeRemaining: training.countdown_sec,
      isPaused: false,
    });
  };

  const stopTraining = () => {
    setActiveTraining(null);
  };

  const togglePause = () => {
    if (activeTraining) {
      setActiveTraining({ ...activeTraining, isPaused: !activeTraining.isPaused });
    }
  };

  const skipStep = () => {
    if (activeTraining && activeTraining.currentStep < activeTraining.totalSteps) {
      setActiveTraining({
        ...activeTraining,
        currentStep: activeTraining.currentStep + 1,
        phase: "DRILLING",
      });
    }
  };

  const estimateDuration = (training: Training) => {
    let totalMs = training.countdown_sec * 1000;
    training.steps.forEach((step) => {
      totalMs += step.count * 2000; // Estimate 2s per ball
      totalMs += step.pause_after_sec * 1000;
    });
    const minutes = Math.round(totalMs / 60000);
    return `${minutes} min`;
  };

  const handleNewTraining = () => {
    setEditingTraining({
      name: "",
      description: "",
      countdown_sec: 15,
      steps: [],
    });
  };

  const handleDeleteTraining = (id: number) => {
    setTrainings(trainings.filter((t) => t.id !== id));
    setShowDeleteConfirm(null);
  };

  return (
    <div className="space-y-6">
      <div className="flex items-center justify-between">
        <h2 className="text-xl font-semibold">{t("nav.training")}</h2>
        <Button onClick={handleNewTraining}>
          <Plus className="mr-2 h-4 w-4" />
          {t("training.new")}
        </Button>
      </div>

      {/* Active Training Overlay */}
      {activeTraining && (
        <Card className="border-primary bg-gradient-to-br from-primary/10 to-primary/5">
          <CardContent className="py-6">
            <div className="flex flex-col items-center text-center">
              <Badge
                variant={
                  activeTraining.phase === "COUNTDOWN"
                    ? "warning"
                    : activeTraining.phase === "DRILLING"
                    ? "success"
                    : activeTraining.phase === "PAUSE"
                    ? "secondary"
                    : "default"
                }
                className="mb-2"
              >
                {t(`training.phase.${activeTraining.phase.toLowerCase()}`)}
              </Badge>

              <h3 className="text-2xl font-bold">{activeTraining.name}</h3>
              <p className="text-muted">
                {t("training.step")} {activeTraining.currentStep} / {activeTraining.totalSteps}:{" "}
                {activeTraining.stepName}
              </p>

              <div className="mt-4 flex items-center gap-4">
                <div className="text-center">
                  <div className="text-4xl font-bold">{activeTraining.currentBall}</div>
                  <div className="text-sm text-muted">/ {activeTraining.totalBalls}</div>
                </div>
                {activeTraining.phase === "COUNTDOWN" && (
                  <div className="flex h-20 w-20 items-center justify-center rounded-full border-4 border-warning">
                    <span className="text-3xl font-bold text-warning">{activeTraining.timeRemaining}</span>
                  </div>
                )}
              </div>

              <Progress
                value={(activeTraining.currentBall / activeTraining.totalBalls) * 100}
                className="mt-4 h-3 w-full max-w-md"
              />

              <div className="mt-6 flex gap-3">
                <Button
                  size="lg"
                  variant={activeTraining.isPaused ? "default" : "secondary"}
                  onClick={togglePause}
                >
                  {activeTraining.isPaused ? (
                    <>
                      <Play className="mr-2 h-5 w-5" /> {t("drills.resume")}
                    </>
                  ) : (
                    <>
                      <Pause className="mr-2 h-5 w-5" /> {t("drills.pause")}
                    </>
                  )}
                </Button>
                <Button size="lg" variant="outline" onClick={skipStep}>
                  <SkipForward className="mr-2 h-5 w-5" /> {t("training.skip")}
                </Button>
                <Button size="lg" variant="destructive" onClick={stopTraining}>
                  <Square className="mr-2 h-5 w-5" /> {t("drills.stop")}
                </Button>
              </div>
            </div>
          </CardContent>
        </Card>
      )}

      {/* Training List */}
      <div className="grid gap-4 md:grid-cols-2">
        {trainings.map((training) => (
          <Card key={training.id}>
            <CardHeader className="pb-3">
              <div className="flex items-start justify-between">
                <div>
                  <CardTitle className="text-base">{training.name}</CardTitle>
                  <p className="text-sm text-muted">{training.description}</p>
                </div>
                <div className="flex items-center gap-1">
                  <Badge variant="secondary" className="gap-1">
                    <Dumbbell className="h-3 w-3" />
                    {training.steps.length} {t("training.steps")}
                  </Badge>
                </div>
              </div>
            </CardHeader>
            <CardContent className="space-y-3">
              <div className="flex flex-wrap gap-2">
                {training.steps.map((step, i) => (
                  <Badge key={i} variant="outline" className="text-xs">
                    {step.drill_name}
                  </Badge>
                ))}
              </div>
              <div className="flex items-center justify-between pt-2">
                <span className="flex items-center gap-1 text-sm text-muted">
                  <Clock className="h-4 w-4" />
                  {estimateDuration(training)}
                </span>
                <div className="flex gap-2">
                  <Button size="sm" onClick={() => startTraining(training)}>
                    <Play className="mr-1 h-3 w-3" />
                    {t("drills.run")}
                  </Button>
                  <Button size="sm" variant="ghost" onClick={() => setEditingTraining(training)}>
                    <Pencil className="h-4 w-4" />
                  </Button>
                  <Button size="sm" variant="ghost" onClick={() => setShowDeleteConfirm(training.id!)}>
                    <Trash2 className="h-4 w-4 text-danger" />
                  </Button>
                </div>
              </div>
            </CardContent>
          </Card>
        ))}
      </div>

      {/* Training Editor Dialog */}
      {editingTraining && (
        <TrainingEditorDialog
          training={editingTraining}
          onClose={() => setEditingTraining(null)}
          onSave={(updated) => {
            if (updated.id) {
              setTrainings(trainings.map((t) => (t.id === updated.id ? updated : t)));
            } else {
              setTrainings([...trainings, { ...updated, id: Date.now() }]);
            }
            setEditingTraining(null);
          }}
          t={t}
        />
      )}

      {/* Delete Confirmation */}
      <Dialog open={showDeleteConfirm !== null} onOpenChange={() => setShowDeleteConfirm(null)}>
        <DialogContent>
          <DialogHeader>
            <DialogTitle>Delete Training?</DialogTitle>
            <DialogDescription>
              This action cannot be undone. Are you sure you want to delete this training?
            </DialogDescription>
          </DialogHeader>
          <DialogFooter>
            <Button variant="outline" onClick={() => setShowDeleteConfirm(null)}>
              {t("common.cancel")}
            </Button>
            <Button variant="destructive" onClick={() => showDeleteConfirm && handleDeleteTraining(showDeleteConfirm)}>
              {t("drills.delete")}
            </Button>
          </DialogFooter>
        </DialogContent>
      </Dialog>
    </div>
  );
}

interface TrainingEditorDialogProps {
  training: Training;
  onClose: () => void;
  onSave: (training: Training) => void;
  t: (key: string) => string;
}

function TrainingEditorDialog({ training, onClose, onSave, t }: TrainingEditorDialogProps) {
  const [name, setName] = useState(training.name);
  const [description, setDescription] = useState(training.description);
  const [countdownSec, setCountdownSec] = useState(training.countdown_sec);
  const [steps, setSteps] = useState<TrainingStep[]>(training.steps);

  const addStep = () => {
    const drill = availableDrills[0];
    setSteps([
      ...steps,
      { drill_id: drill.id, drill_name: drill.name, count: 60, percent: 100, pause_after_sec: 30 },
    ]);
  };

  const removeStep = (index: number) => {
    setSteps(steps.filter((_, i) => i !== index));
  };

  const updateStep = (index: number, updates: Partial<TrainingStep>) => {
    setSteps(steps.map((step, i) => (i === index ? { ...step, ...updates } : step)));
  };

  const moveStep = (index: number, direction: "up" | "down") => {
    if (
      (direction === "up" && index === 0) ||
      (direction === "down" && index === steps.length - 1)
    ) {
      return;
    }
    const newSteps = [...steps];
    const swapIndex = direction === "up" ? index - 1 : index + 1;
    [newSteps[index], newSteps[swapIndex]] = [newSteps[swapIndex], newSteps[index]];
    setSteps(newSteps);
  };

  const handleDrillChange = (index: number, drillId: string) => {
    const drill = availableDrills.find((d) => d.id === parseInt(drillId));
    if (drill) {
      updateStep(index, { drill_id: drill.id, drill_name: drill.name });
    }
  };

  return (
    <Dialog open onOpenChange={onClose}>
      <DialogContent className="max-w-2xl max-h-[80vh] overflow-hidden flex flex-col">
        <DialogHeader>
          <DialogTitle>{training.id ? "Edit Training" : "New Training"}</DialogTitle>
        </DialogHeader>
        <div className="flex-1 space-y-4 overflow-auto py-4">
          <div className="grid gap-4 sm:grid-cols-2">
            <div>
              <label className="text-sm font-medium">{t("common.name")}</label>
              <Input value={name} onChange={(e) => setName(e.target.value)} className="mt-1" />
            </div>
            <div>
              <label className="text-sm font-medium">{t("training.countdown")} (s)</label>
              <div className="mt-1">
                <Slider
                  value={[countdownSec]}
                  min={3}
                  max={120}
                  step={1}
                  onValueChange={(v) => setCountdownSec(v[0])}
                />
                <span className="mt-1 block text-center text-sm">{countdownSec}s</span>
              </div>
            </div>
          </div>
          <div>
            <label className="text-sm font-medium">{t("common.description")}</label>
            <Input value={description} onChange={(e) => setDescription(e.target.value)} className="mt-1" />
          </div>

          <div>
            <div className="mb-2 flex items-center justify-between">
              <label className="text-sm font-medium">Steps ({steps.length})</label>
              <Button size="sm" variant="outline" onClick={addStep}>
                <Plus className="mr-1 h-3 w-3" />
                Add Step
              </Button>
            </div>
            <div className="space-y-2">
              {steps.map((step, i) => (
                <div
                  key={i}
                  className="flex items-center gap-2 rounded-lg border border-border bg-surface-2 p-3"
                >
                  <div className="flex flex-col gap-1">
                    <Button size="sm" variant="ghost" className="h-6 w-6 p-0" onClick={() => moveStep(i, "up")}>
                      <ChevronUp className="h-4 w-4" />
                    </Button>
                    <Button size="sm" variant="ghost" className="h-6 w-6 p-0" onClick={() => moveStep(i, "down")}>
                      <ChevronDown className="h-4 w-4" />
                    </Button>
                  </div>
                  <div className="flex-1 grid gap-2 sm:grid-cols-4">
                    <Select
                      value={step.drill_id.toString()}
                      onValueChange={(v) => handleDrillChange(i, v)}
                    >
                      <SelectTrigger className="h-8">
                        <SelectValue />
                      </SelectTrigger>
                      <SelectContent>
                        {availableDrills.map((drill) => (
                          <SelectItem key={drill.id} value={drill.id.toString()}>
                            {drill.name}
                          </SelectItem>
                        ))}
                      </SelectContent>
                    </Select>
                    <div>
                      <label className="text-[10px] text-muted">Balls</label>
                      <Input
                        type="number"
                        value={step.count}
                        onChange={(e) => updateStep(i, { count: parseInt(e.target.value) || 1 })}
                        className="h-8"
                        min={1}
                        max={999}
                      />
                    </div>
                    <div>
                      <label className="text-[10px] text-muted">Speed %</label>
                      <Input
                        type="number"
                        value={step.percent}
                        onChange={(e) => updateStep(i, { percent: parseInt(e.target.value) || 100 })}
                        className="h-8"
                        min={50}
                        max={150}
                      />
                    </div>
                    <div>
                      <label className="text-[10px] text-muted">Pause (s)</label>
                      <Input
                        type="number"
                        value={step.pause_after_sec}
                        onChange={(e) => updateStep(i, { pause_after_sec: parseInt(e.target.value) || 0 })}
                        className="h-8"
                        min={0}
                        max={600}
                      />
                    </div>
                  </div>
                  <Button size="sm" variant="ghost" onClick={() => removeStep(i)}>
                    <Trash2 className="h-4 w-4 text-danger" />
                  </Button>
                </div>
              ))}
              {steps.length === 0 && (
                <p className="py-8 text-center text-sm text-muted">
                  No steps yet. Click "Add Step" to begin.
                </p>
              )}
            </div>
          </div>
        </div>
        <DialogFooter>
          <Button variant="outline" onClick={onClose}>
            {t("common.cancel")}
          </Button>
          <Button
            onClick={() => {
              onSave({ ...training, name, description, countdown_sec: countdownSec, steps });
            }}
            disabled={!name || steps.length === 0}
          >
            {t("common.save")}
          </Button>
        </DialogFooter>
      </DialogContent>
    </Dialog>
  );
}
