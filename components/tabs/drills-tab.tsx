"use client";

import { useState } from "react";
import { useApp } from "@/lib/store";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Button } from "@/components/ui/button";
import { Badge } from "@/components/ui/badge";
import { Input } from "@/components/ui/input";
import { Progress } from "@/components/ui/progress";
import { ScrollArea } from "@/components/ui/scroll-area";
import {
  Dialog,
  DialogContent,
  DialogDescription,
  DialogFooter,
  DialogHeader,
  DialogTitle,
} from "@/components/ui/dialog";
import {
  Collapsible,
  CollapsibleContent,
  CollapsibleTrigger,
} from "@/components/ui/collapsible";
import {
  DropdownMenu,
  DropdownMenuContent,
  DropdownMenuItem,
  DropdownMenuTrigger,
} from "@/components/ui/dropdown-menu";
import {
  ChevronRight,
  ChevronDown,
  Play,
  Pause,
  Square,
  Pencil,
  MoreHorizontal,
  FolderPlus,
  Lock,
  Plus,
  Trash2,
  Move,
  RotateCcw,
} from "lucide-react";
import type { DrillFolder, Drill, Ball } from "@/lib/types";

// Sample data
const sampleFolders: DrillFolder[] = [
  {
    id: 1,
    name: "Introductory",
    description: "Drills for beginners",
    sort_order: 0,
    readonly: true,
    drills: [
      {
        id: 1,
        name: "Forehand Warmup",
        description: "Warmup drill with topspin serve to the forehand",
        balls: [{ top_speed: 120, bot_speed: 0, oscillation: 164, height: 116, rotation: 150, wait_ms: 2100 }],
        repeat: 0,
        sort_order: 0,
        readonly: true,
      },
      {
        id: 2,
        name: "Backhand Warmup",
        description: "Warmup drill with topspin serve to the backhand",
        balls: [{ top_speed: 120, bot_speed: 0, oscillation: 136, height: 116, rotation: 150, wait_ms: 2100 }],
        repeat: 0,
        sort_order: 1,
        readonly: true,
      },
    ],
  },
  {
    id: 2,
    name: "My Drills",
    description: "Custom drills",
    sort_order: 1,
    readonly: false,
    drills: [
      {
        id: 3,
        name: "Custom Topspin",
        description: "My custom topspin drill",
        balls: [
          { top_speed: 150, bot_speed: -20, oscillation: 160, height: 180, rotation: 150, wait_ms: 1800 },
          { top_speed: 150, bot_speed: -20, oscillation: 140, height: 180, rotation: 150, wait_ms: 1800 },
        ],
        repeat: 0,
        sort_order: 0,
        readonly: false,
      },
    ],
  },
];

export function DrillsTab() {
  const { activeDrill, setActiveDrill, t } = useApp();
  const [folders, setFolders] = useState<DrillFolder[]>(sampleFolders);
  const [expandedFolders, setExpandedFolders] = useState<number[]>([1, 2]);
  const [editingDrill, setEditingDrill] = useState<Drill | null>(null);
  const [showNewFolderDialog, setShowNewFolderDialog] = useState(false);
  const [newFolderName, setNewFolderName] = useState("");
  const [showMoveDialog, setShowMoveDialog] = useState<{ drill: Drill; folderId: number } | null>(null);

  const toggleFolder = (folderId: number) => {
    setExpandedFolders((prev) =>
      prev.includes(folderId) ? prev.filter((id) => id !== folderId) : [...prev, folderId]
    );
  };

  const startDrill = (drill: Drill) => {
    const totalBalls = drill.balls.length * (drill.repeat || 60);
    setActiveDrill({
      name: drill.name,
      currentBall: 1,
      totalBalls,
      isPaused: false,
      currentParams: {
        top: drill.balls[0].top_speed,
        bot: drill.balls[0].bot_speed,
        osc: drill.balls[0].oscillation,
        height: drill.balls[0].height,
        rot: drill.balls[0].rotation,
      },
    });
  };

  const stopDrill = () => {
    setActiveDrill(null);
  };

  const togglePause = () => {
    if (activeDrill) {
      setActiveDrill({ ...activeDrill, isPaused: !activeDrill.isPaused });
    }
  };

  return (
    <div className="space-y-4">
      <div className="flex items-center justify-between">
        <h2 className="text-xl font-semibold">{t("nav.drills")}</h2>
        <Button size="sm" onClick={() => setShowNewFolderDialog(true)}>
          <FolderPlus className="mr-2 h-4 w-4" />
          {t("drills.new_folder")}
        </Button>
      </div>

      {/* Active Drill Overlay */}
      {activeDrill && (
        <Card className="border-primary bg-primary/5">
          <CardContent className="py-4">
            <div className="flex items-center justify-between">
              <div>
                <p className="text-sm text-muted">{t("drills.active")}</p>
                <h3 className="text-lg font-semibold">{activeDrill.name}</h3>
              </div>
              <div className="flex items-center gap-2">
                <span className="text-2xl font-bold">
                  {activeDrill.currentBall} / {activeDrill.totalBalls}
                </span>
              </div>
            </div>
            <Progress
              value={(activeDrill.currentBall / activeDrill.totalBalls) * 100}
              className="mt-3 h-2"
            />
            <div className="mt-3 flex flex-wrap gap-2">
              <Badge variant="secondary">Top: {activeDrill.currentParams.top}</Badge>
              <Badge variant="secondary">Bot: {activeDrill.currentParams.bot}</Badge>
              <Badge variant="secondary">Osc: {activeDrill.currentParams.osc}</Badge>
              <Badge variant="secondary">H: {activeDrill.currentParams.height}</Badge>
              <Badge variant="secondary">Rot: {activeDrill.currentParams.rot}</Badge>
            </div>
            <div className="mt-4 flex gap-2">
              <Button variant={activeDrill.isPaused ? "default" : "secondary"} onClick={togglePause}>
                {activeDrill.isPaused ? (
                  <>
                    <Play className="mr-2 h-4 w-4" /> {t("drills.resume")}
                  </>
                ) : (
                  <>
                    <Pause className="mr-2 h-4 w-4" /> {t("drills.pause")}
                  </>
                )}
              </Button>
              <Button variant="destructive" onClick={stopDrill}>
                <Square className="mr-2 h-4 w-4" /> {t("drills.stop")}
              </Button>
            </div>
          </CardContent>
        </Card>
      )}

      {/* Folder Tree */}
      <div className="grid gap-6 lg:grid-cols-3">
        <div className="lg:col-span-1">
          <Card>
            <CardHeader className="pb-3">
              <CardTitle className="text-sm font-medium text-muted">Folders</CardTitle>
            </CardHeader>
            <CardContent className="p-0">
              <ScrollArea className="h-[500px]">
                <div className="p-3 pt-0">
                  {folders.map((folder) => (
                    <Collapsible
                      key={folder.id}
                      open={expandedFolders.includes(folder.id!)}
                      onOpenChange={() => toggleFolder(folder.id!)}
                    >
                      <CollapsibleTrigger className="flex w-full items-center gap-2 rounded-lg p-2 text-left hover:bg-surface-2">
                        {expandedFolders.includes(folder.id!) ? (
                          <ChevronDown className="h-4 w-4 text-muted" />
                        ) : (
                          <ChevronRight className="h-4 w-4 text-muted" />
                        )}
                        {folder.readonly && <Lock className="h-3 w-3 text-muted" />}
                        <span className="flex-1 text-sm font-medium">{folder.name}</span>
                        <Badge variant="secondary" className="text-[10px]">
                          {folder.drills.length}
                        </Badge>
                      </CollapsibleTrigger>
                      <CollapsibleContent>
                        <div className="ml-6 space-y-1 border-l border-border pl-3">
                          {folder.drills.map((drill) => (
                            <div
                              key={drill.id}
                              className="flex items-center justify-between rounded-md p-1.5 text-sm hover:bg-surface-2"
                            >
                              <span className="truncate">{drill.name}</span>
                            </div>
                          ))}
                        </div>
                      </CollapsibleContent>
                    </Collapsible>
                  ))}
                </div>
              </ScrollArea>
            </CardContent>
          </Card>
        </div>

        {/* Drill List */}
        <div className="lg:col-span-2">
          <Card>
            <CardHeader className="pb-3">
              <CardTitle className="text-sm font-medium text-muted">Drills</CardTitle>
            </CardHeader>
            <CardContent className="p-0">
              <ScrollArea className="h-[500px]">
                <div className="space-y-2 p-3 pt-0">
                  {folders.flatMap((folder) =>
                    folder.drills.map((drill) => (
                      <DrillCard
                        key={`${folder.id}-${drill.id}`}
                        drill={drill}
                        folder={folder}
                        onRun={() => startDrill(drill)}
                        onEdit={() => setEditingDrill(drill)}
                        onMove={() => setShowMoveDialog({ drill, folderId: folder.id! })}
                        t={t}
                      />
                    ))
                  )}
                </div>
              </ScrollArea>
            </CardContent>
          </Card>
        </div>
      </div>

      {/* New Folder Dialog */}
      <Dialog open={showNewFolderDialog} onOpenChange={setShowNewFolderDialog}>
        <DialogContent>
          <DialogHeader>
            <DialogTitle>{t("drills.new_folder")}</DialogTitle>
          </DialogHeader>
          <Input
            value={newFolderName}
            onChange={(e) => setNewFolderName(e.target.value)}
            placeholder="Folder name"
          />
          <DialogFooter>
            <Button variant="outline" onClick={() => setShowNewFolderDialog(false)}>
              {t("common.cancel")}
            </Button>
            <Button
              onClick={() => {
                if (newFolderName) {
                  setFolders([
                    ...folders,
                    {
                      id: Date.now(),
                      name: newFolderName,
                      description: "",
                      sort_order: folders.length,
                      readonly: false,
                      drills: [],
                    },
                  ]);
                  setNewFolderName("");
                  setShowNewFolderDialog(false);
                }
              }}
            >
              Create
            </Button>
          </DialogFooter>
        </DialogContent>
      </Dialog>

      {/* Edit Drill Dialog */}
      {editingDrill && (
        <DrillEditorDialog
          drill={editingDrill}
          onClose={() => setEditingDrill(null)}
          onSave={(updated) => {
            // Update drill in state
            setEditingDrill(null);
          }}
          t={t}
        />
      )}

      {/* Move Drill Dialog */}
      {showMoveDialog && (
        <Dialog open={true} onOpenChange={() => setShowMoveDialog(null)}>
          <DialogContent>
            <DialogHeader>
              <DialogTitle>Move "{showMoveDialog.drill.name}"</DialogTitle>
              <DialogDescription>Select destination folder</DialogDescription>
            </DialogHeader>
            <div className="space-y-2">
              {folders
                .filter((f) => !f.readonly && f.id !== showMoveDialog.folderId)
                .map((folder) => (
                  <Button
                    key={folder.id}
                    variant="outline"
                    className="w-full justify-start"
                    onClick={() => setShowMoveDialog(null)}
                  >
                    {folder.name}
                  </Button>
                ))}
            </div>
          </DialogContent>
        </Dialog>
      )}
    </div>
  );
}

interface DrillCardProps {
  drill: Drill;
  folder: DrillFolder;
  onRun: () => void;
  onEdit: () => void;
  onMove: () => void;
  t: (key: string) => string;
}

function DrillCard({ drill, folder, onRun, onEdit, onMove, t }: DrillCardProps) {
  return (
    <div className="flex items-center gap-3 rounded-lg border border-border bg-surface p-3 transition-colors hover:bg-surface-2">
      <div className="flex-1 min-w-0">
        <div className="flex items-center gap-2">
          <span className="font-medium">{drill.name}</span>
          {drill.readonly && (
            <Badge variant="secondary" className="text-[10px]">
              {t("drills.factory")}
            </Badge>
          )}
        </div>
        <p className="truncate text-sm text-muted">{drill.description}</p>
        <div className="mt-1 flex items-center gap-2">
          <Badge variant="outline" className="text-[10px]">
            {drill.balls.length} {t("drills.balls")}
          </Badge>
        </div>
      </div>
      <div className="flex items-center gap-1">
        <Button size="sm" onClick={onRun}>
          <Play className="mr-1 h-3 w-3" />
          {t("drills.run")}
        </Button>
        {!drill.readonly && (
          <>
            <Button size="sm" variant="ghost" onClick={onEdit}>
              <Pencil className="h-4 w-4" />
            </Button>
            <DropdownMenu>
              <DropdownMenuTrigger asChild>
                <Button size="sm" variant="ghost">
                  <MoreHorizontal className="h-4 w-4" />
                </Button>
              </DropdownMenuTrigger>
              <DropdownMenuContent align="end">
                <DropdownMenuItem onClick={onMove}>
                  <Move className="mr-2 h-4 w-4" />
                  {t("drills.move")}
                </DropdownMenuItem>
                <DropdownMenuItem className="text-danger">
                  <Trash2 className="mr-2 h-4 w-4" />
                  {t("drills.delete")}
                </DropdownMenuItem>
              </DropdownMenuContent>
            </DropdownMenu>
          </>
        )}
      </div>
    </div>
  );
}

interface DrillEditorDialogProps {
  drill: Drill;
  onClose: () => void;
  onSave: (drill: Drill) => void;
  t: (key: string) => string;
}

function DrillEditorDialog({ drill, onClose, onSave, t }: DrillEditorDialogProps) {
  const [name, setName] = useState(drill.name);
  const [description, setDescription] = useState(drill.description);
  const [balls, setBalls] = useState<Ball[]>(drill.balls);
  const [repeat, setRepeat] = useState(drill.repeat);

  const addBall = () => {
    setBalls([
      ...balls,
      { top_speed: 80, bot_speed: 0, oscillation: 150, height: 150, rotation: 150, wait_ms: 2000 },
    ]);
  };

  const removeBall = (index: number) => {
    setBalls(balls.filter((_, i) => i !== index));
  };

  const updateBall = (index: number, field: keyof Ball, value: number) => {
    setBalls(balls.map((ball, i) => (i === index ? { ...ball, [field]: value } : ball)));
  };

  return (
    <Dialog open onOpenChange={onClose}>
      <DialogContent className="max-w-3xl max-h-[80vh] overflow-hidden flex flex-col">
        <DialogHeader>
          <DialogTitle>{t("drills.edit")}: {drill.name}</DialogTitle>
        </DialogHeader>
        <div className="flex-1 space-y-4 overflow-auto py-4">
          <div className="grid gap-4 sm:grid-cols-2">
            <div>
              <label className="text-sm font-medium">{t("common.name")}</label>
              <Input value={name} onChange={(e) => setName(e.target.value)} className="mt-1" />
            </div>
            <div>
              <label className="text-sm font-medium">Repeat</label>
              <Input
                type="number"
                value={repeat}
                onChange={(e) => setRepeat(parseInt(e.target.value) || 0)}
                className="mt-1"
                min={0}
              />
            </div>
          </div>
          <div>
            <label className="text-sm font-medium">{t("common.description")}</label>
            <Input value={description} onChange={(e) => setDescription(e.target.value)} className="mt-1" />
          </div>

          <div>
            <div className="mb-2 flex items-center justify-between">
              <label className="text-sm font-medium">Balls ({balls.length})</label>
              <Button size="sm" variant="outline" onClick={addBall}>
                <Plus className="mr-1 h-3 w-3" />
                Add Ball
              </Button>
            </div>
            <div className="rounded-lg border border-border">
              <table className="w-full text-sm">
                <thead className="border-b border-border bg-surface-2">
                  <tr>
                    <th className="p-2 text-left font-medium">#</th>
                    <th className="p-2 text-left font-medium">Top</th>
                    <th className="p-2 text-left font-medium">Bot</th>
                    <th className="p-2 text-left font-medium">Osc</th>
                    <th className="p-2 text-left font-medium">Height</th>
                    <th className="p-2 text-left font-medium">Rot</th>
                    <th className="p-2 text-left font-medium">Wait</th>
                    <th className="p-2"></th>
                  </tr>
                </thead>
                <tbody>
                  {balls.map((ball, i) => (
                    <tr key={i} className="border-b border-border last:border-0">
                      <td className="p-2 text-muted">{i + 1}</td>
                      <td className="p-2">
                        <Input
                          type="number"
                          value={ball.top_speed}
                          onChange={(e) => updateBall(i, "top_speed", parseInt(e.target.value))}
                          className="h-8 w-16"
                        />
                      </td>
                      <td className="p-2">
                        <Input
                          type="number"
                          value={ball.bot_speed}
                          onChange={(e) => updateBall(i, "bot_speed", parseInt(e.target.value))}
                          className="h-8 w-16"
                        />
                      </td>
                      <td className="p-2">
                        <Input
                          type="number"
                          value={ball.oscillation}
                          onChange={(e) => updateBall(i, "oscillation", parseInt(e.target.value))}
                          className="h-8 w-16"
                        />
                      </td>
                      <td className="p-2">
                        <Input
                          type="number"
                          value={ball.height}
                          onChange={(e) => updateBall(i, "height", parseInt(e.target.value))}
                          className="h-8 w-16"
                        />
                      </td>
                      <td className="p-2">
                        <Input
                          type="number"
                          value={ball.rotation}
                          onChange={(e) => updateBall(i, "rotation", parseInt(e.target.value))}
                          className="h-8 w-16"
                        />
                      </td>
                      <td className="p-2">
                        <Input
                          type="number"
                          value={ball.wait_ms}
                          onChange={(e) => updateBall(i, "wait_ms", parseInt(e.target.value))}
                          className="h-8 w-20"
                        />
                      </td>
                      <td className="p-2">
                        <Button size="sm" variant="ghost" onClick={() => removeBall(i)}>
                          <Trash2 className="h-4 w-4 text-danger" />
                        </Button>
                      </td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          </div>
        </div>
        <DialogFooter>
          <Button variant="outline" onClick={onClose}>
            {t("common.cancel")}
          </Button>
          <Button
            onClick={() => {
              onSave({ ...drill, name, description, balls, repeat });
            }}
          >
            {t("common.save")}
          </Button>
        </DialogFooter>
      </DialogContent>
    </Dialog>
  );
}
