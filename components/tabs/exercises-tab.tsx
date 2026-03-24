"use client";

import { useState } from "react";
import { useApp } from "@/lib/store";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Button } from "@/components/ui/button";
import { Badge } from "@/components/ui/badge";
import { Slider } from "@/components/ui/slider";
import {
  Collapsible,
  CollapsibleContent,
  CollapsibleTrigger,
} from "@/components/ui/collapsible";
import {
  Dialog,
  DialogContent,
  DialogHeader,
  DialogTitle,
} from "@/components/ui/dialog";
import { ChevronDown, ChevronRight, Play, RotateCcw, Clock } from "lucide-react";
import type { ExerciseCategory, Exercise } from "@/lib/types";

// Default exercises data
const defaultExercises: ExerciseCategory[] = [
  {
    name: "Warmup",
    icon: "fire",
    exercises: [
      { name: "Jogging in Place", duration_sec: 60, description: "Jog in place with light, bouncy steps, keeping knees slightly bent." },
      { name: "Arm Circles", duration_sec: 30, description: "Extend arms to sides, make small circles growing to large circles." },
      { name: "Wrist Rotations", duration_sec: 30, description: "Hold arms in front, rotate wrists in circles." },
      { name: "Trunk Rotations", duration_sec: 45, description: "Feet shoulder-width, rotate upper body left-right." },
      { name: "Hip Circles", duration_sec: 30, description: "Hands on hips, make large circular motions." },
      { name: "High Knees", duration_sec: 45, description: "Jog in place driving knees to waist height." },
      { name: "Dynamic Lunges", duration_sec: 60, description: "Step forward into lunge, alternate legs." },
      { name: "Shadow Play", duration_sec: 90, description: "Perform forehand and backhand strokes with proper footwork." },
    ],
  },
  {
    name: "Footwork",
    icon: "footprints",
    exercises: [
      { name: "Side Shuffle", duration_sec: 60, description: "Shuffle laterally from forehand to backhand corner and back." },
      { name: "Crossover Step", duration_sec: 60, description: "From backhand corner, cross right foot over left to reach forehand corner." },
      { name: "Falkenberg Footwork", duration_sec: 120, description: "Classic 3-point footwork pattern used by professionals." },
      { name: "In-Out Movement", duration_sec: 60, description: "Step in toward table for short ball, quickly step back for deep ball." },
      { name: "Two-Point Rally", duration_sec: 90, description: "Ball alternates to FH and BH. Move using shuffle steps." },
      { name: "Triangle Footwork", duration_sec: 90, description: "3 markers in triangle behind table. Move to each using shuffle steps." },
      { name: "Pivot Drill", duration_sec: 60, description: "From BH corner, pivot around left foot to play forehand." },
    ],
  },
  {
    name: "Conditioning",
    icon: "zap",
    exercises: [
      { name: "Reaction Ball", duration_sec: 60, description: "Drop/throw reaction ball against floor or wall, catch quickly." },
      { name: "Fast Hands Counter", duration_sec: 120, description: "Stand close to table, rally fast counter-drives." },
      { name: "Multi-Ball Speed", duration_sec: 90, description: "Feeder rapidly sends balls to alternating locations." },
      { name: "Quick-Fire Serves", duration_sec: 90, description: "Serve 20-30 balls in rapid succession with minimal pause." },
    ],
  },
  {
    name: "Core",
    icon: "activity",
    exercises: [
      { name: "Box Jumps", duration_sec: 60, description: "Jump onto low box with both feet, land softly in squat." },
      { name: "Bodyweight Squats", duration_sec: 60, description: "Feet shoulder-width, lower until thighs parallel, drive up." },
      { name: "Forearm Plank", duration_sec: 45, description: "Hold plank on forearms, body straight head-to-heels." },
      { name: "Side Plank", duration_sec: 30, description: "Support on forearm, feet stacked, hips lifted in line." },
      { name: "Resistance Band FH", duration_sec: 60, description: "Band at waist height behind you, perform forehand motion." },
      { name: "Calf Raises", duration_sec: 45, description: "Rise on balls of feet, lower slowly." },
    ],
  },
];

const categoryIcons: Record<string, string> = {
  "Warmup": "fire",
  "Footwork": "footprints",
  "Conditioning": "zap",
  "Core": "activity",
};

const categoryEmojis: Record<string, string> = {
  "Warmup": "W",
  "Footwork": "F",
  "Conditioning": "C",
  "Core": "S",
};

export function ExercisesTab() {
  const { t } = useApp();
  const [categories, setCategories] = useState<ExerciseCategory[]>(defaultExercises);
  const [expandedCategories, setExpandedCategories] = useState<string[]>(["Warmup"]);
  const [editingExercise, setEditingExercise] = useState<{ category: string; exercise: Exercise } | null>(null);
  const [runningExercise, setRunningExercise] = useState<Exercise | null>(null);

  const toggleCategory = (categoryName: string) => {
    setExpandedCategories((prev) =>
      prev.includes(categoryName)
        ? prev.filter((name) => name !== categoryName)
        : [...prev, categoryName]
    );
  };

  const updateExerciseDuration = (categoryName: string, exerciseName: string, newDuration: number) => {
    setCategories(
      categories.map((cat) =>
        cat.name === categoryName
          ? {
              ...cat,
              exercises: cat.exercises.map((ex) =>
                ex.name === exerciseName ? { ...ex, duration_sec: newDuration } : ex
              ),
            }
          : cat
      )
    );
  };

  const resetAllDurations = () => {
    setCategories(defaultExercises);
  };

  const formatDuration = (seconds: number) => {
    if (seconds < 60) return `${seconds}s`;
    const mins = Math.floor(seconds / 60);
    const secs = seconds % 60;
    return secs > 0 ? `${mins}m ${secs}s` : `${mins}m`;
  };

  const runSolo = (exercise: Exercise) => {
    setRunningExercise(exercise);
    // In real implementation, this would start a timer
  };

  return (
    <div className="space-y-4">
      <div className="flex items-center justify-between">
        <h2 className="text-xl font-semibold">{t("nav.exercises")}</h2>
        <Button variant="outline" onClick={resetAllDurations}>
          <RotateCcw className="mr-2 h-4 w-4" />
          {t("exercises.reset_durations")}
        </Button>
      </div>

      <div className="space-y-4">
        {categories.map((category) => (
          <Card key={category.name}>
            <Collapsible
              open={expandedCategories.includes(category.name)}
              onOpenChange={() => toggleCategory(category.name)}
            >
              <CollapsibleTrigger asChild>
                <CardHeader className="cursor-pointer py-4 hover:bg-surface-2">
                  <div className="flex items-center gap-3">
                    {expandedCategories.includes(category.name) ? (
                      <ChevronDown className="h-5 w-5 text-muted" />
                    ) : (
                      <ChevronRight className="h-5 w-5 text-muted" />
                    )}
                    <div className="flex h-8 w-8 items-center justify-center rounded-lg bg-primary/20 text-primary font-bold">
                      {categoryEmojis[category.name] || category.name[0]}
                    </div>
                    <CardTitle className="text-base">{category.name}</CardTitle>
                    <Badge variant="secondary" className="ml-auto">
                      {category.exercises.length} exercises
                    </Badge>
                  </div>
                </CardHeader>
              </CollapsibleTrigger>
              <CollapsibleContent>
                <CardContent className="pt-0">
                  <div className="grid gap-3 sm:grid-cols-2 lg:grid-cols-3">
                    {category.exercises.map((exercise) => (
                      <ExerciseCard
                        key={exercise.name}
                        exercise={exercise}
                        onDurationClick={() =>
                          setEditingExercise({ category: category.name, exercise })
                        }
                        onRunSolo={() => runSolo(exercise)}
                        formatDuration={formatDuration}
                        t={t}
                      />
                    ))}
                  </div>
                </CardContent>
              </CollapsibleContent>
            </Collapsible>
          </Card>
        ))}
      </div>

      {/* Duration Editor Dialog */}
      {editingExercise && (
        <DurationEditorDialog
          exercise={editingExercise.exercise}
          onClose={() => setEditingExercise(null)}
          onSave={(duration) => {
            updateExerciseDuration(
              editingExercise.category,
              editingExercise.exercise.name,
              duration
            );
            setEditingExercise(null);
          }}
          formatDuration={formatDuration}
        />
      )}

      {/* Running Exercise Dialog */}
      {runningExercise && (
        <Dialog open onOpenChange={() => setRunningExercise(null)}>
          <DialogContent>
            <DialogHeader>
              <DialogTitle>{runningExercise.name}</DialogTitle>
            </DialogHeader>
            <div className="flex flex-col items-center gap-4 py-8">
              <div className="flex h-24 w-24 items-center justify-center rounded-full border-4 border-primary text-4xl font-bold">
                {runningExercise.duration_sec}
              </div>
              <p className="text-center text-muted">{runningExercise.description}</p>
              <Button variant="destructive" onClick={() => setRunningExercise(null)}>
                Stop
              </Button>
            </div>
          </DialogContent>
        </Dialog>
      )}
    </div>
  );
}

interface ExerciseCardProps {
  exercise: Exercise;
  onDurationClick: () => void;
  onRunSolo: () => void;
  formatDuration: (seconds: number) => string;
  t: (key: string) => string;
}

function ExerciseCard({ exercise, onDurationClick, onRunSolo, formatDuration, t }: ExerciseCardProps) {
  return (
    <div className="rounded-lg border border-border bg-surface-2 p-3">
      <div className="flex items-start justify-between gap-2">
        <div className="flex-1 min-w-0">
          <h4 className="font-medium text-sm">{exercise.name}</h4>
          <p className="mt-1 text-xs text-muted line-clamp-2">{exercise.description}</p>
        </div>
      </div>
      <div className="mt-3 flex items-center justify-between">
        <button
          onClick={onDurationClick}
          className="flex items-center gap-1 rounded-md border border-border bg-background px-2 py-1 text-sm hover:border-primary"
        >
          <Clock className="h-3 w-3 text-muted" />
          {formatDuration(exercise.duration_sec)}
        </button>
        <Button size="sm" variant="ghost" onClick={onRunSolo}>
          <Play className="mr-1 h-3 w-3" />
          {t("exercises.run_solo")}
        </Button>
      </div>
    </div>
  );
}

interface DurationEditorDialogProps {
  exercise: Exercise;
  onClose: () => void;
  onSave: (duration: number) => void;
  formatDuration: (seconds: number) => string;
}

function DurationEditorDialog({ exercise, onClose, onSave, formatDuration }: DurationEditorDialogProps) {
  const [duration, setDuration] = useState(exercise.duration_sec);

  return (
    <Dialog open onOpenChange={onClose}>
      <DialogContent>
        <DialogHeader>
          <DialogTitle>Edit Duration: {exercise.name}</DialogTitle>
        </DialogHeader>
        <div className="space-y-6 py-4">
          <div className="text-center">
            <span className="text-4xl font-bold">{formatDuration(duration)}</span>
          </div>
          <Slider
            value={[duration]}
            min={10}
            max={300}
            step={5}
            onValueChange={(v) => setDuration(v[0])}
          />
          <div className="flex justify-between text-sm text-muted">
            <span>10s</span>
            <span>5m</span>
          </div>
        </div>
        <div className="flex justify-end gap-2">
          <Button variant="outline" onClick={onClose}>
            Cancel
          </Button>
          <Button onClick={() => onSave(duration)}>Save</Button>
        </div>
      </DialogContent>
    </Dialog>
  );
}
