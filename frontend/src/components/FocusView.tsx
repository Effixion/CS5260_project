"use client";

import { useState } from "react";
import { Check, ChevronLeft } from "lucide-react";
import { api, type Message } from "@/lib/api";
import { useProject } from "@/contexts/ProjectContext";
import { ResultsView } from "@/components/ResultsView";
import { Button } from "@/components/ui/button";
import { Card, CardContent } from "@/components/ui/card";
import type { FocusContent } from "@/app/project/[id]/page";

interface FocusViewProps {
  projectId: string;
  content: NonNullable<FocusContent>;
  onClose: () => void;
}

function LargeVisualizationPicker({
  projectId,
  messageId,
  onClose,
}: {
  projectId: string;
  messageId: string;
  onClose: () => void;
}) {
  const { artifacts, refreshFiles } = useProject();
  const [selected, setSelected] = useState<Set<string>>(new Set());
  const [confirming, setConfirming] = useState(false);

  const plotArtifacts = artifacts.filter((a) =>
    a.filename.startsWith("candidate_plot_")
  );

  const toggle = (filename: string) => {
    setSelected((prev) => {
      const next = new Set(prev);
      if (next.has(filename)) next.delete(filename);
      else next.add(filename);
      return next;
    });
  };

  const handleConfirm = async () => {
    if (selected.size === 0 || confirming) return;
    setConfirming(true);
    try {
      const response = await api.selectVisualizationsStream(
        projectId,
        messageId,
        Array.from(selected)
      );
      if (response.body) {
        const reader = response.body.getReader();
        while (true) {
          const { done } = await reader.read();
          if (done) break;
        }
      }
      refreshFiles();
      onClose();
    } finally {
      setConfirming(false);
    }
  };

  return (
    <div className="flex flex-1 flex-col overflow-y-auto p-6">
      <div className="mx-auto w-full max-w-5xl space-y-6">
        <div className="flex items-center justify-between">
          <h2 className="text-xl font-semibold text-foreground">
            Select Visualizations
          </h2>
          <Button variant="outline" onClick={onClose}>
            <ChevronLeft className="mr-1 h-4 w-4" />
            Back to Chat
          </Button>
        </div>

        <p className="text-sm text-muted-foreground">
          Click to select the visualizations you want in your presentation.
        </p>

        <div className="grid grid-cols-2 gap-4 lg:grid-cols-3">
          {plotArtifacts.map((artifact) => {
            const isSelected = selected.has(artifact.filename);
            return (
              <button
                key={artifact.filename}
                onClick={() => toggle(artifact.filename)}
                className={`relative overflow-hidden rounded-lg border-2 transition-all ${
                  isSelected
                    ? "border-primary ring-2 ring-primary/30"
                    : "border-border hover:border-primary-light"
                }`}
              >
                <div className="aspect-[4/3] bg-background">
                  <img
                    src={api.getArtifactUrl(projectId, artifact.filename)}
                    alt={artifact.filename}
                    className="h-full w-full object-contain"
                  />
                </div>
                <Card className="rounded-none border-0 border-t">
                  <CardContent className="px-3 py-2 text-left text-sm text-muted-foreground">
                    {artifact.filename}
                  </CardContent>
                </Card>
                {isSelected && (
                  <div className="absolute top-2 right-2 flex h-6 w-6 items-center justify-center rounded-full bg-primary text-white">
                    <Check className="h-3.5 w-3.5" />
                  </div>
                )}
              </button>
            );
          })}
        </div>

        <div className="flex gap-3">
          <Button
            onClick={handleConfirm}
            disabled={selected.size === 0 || confirming}
          >
            {confirming
              ? "Generating..."
              : `Confirm Selection (${selected.size})`}
          </Button>
          <Button variant="outline" onClick={onClose}>
            Cancel
          </Button>
        </div>
      </div>
    </div>
  );
}

export function FocusView({ projectId, content, onClose }: FocusViewProps) {
  if (content.type === "results") {
    return <ResultsView projectId={projectId} onBackToChat={onClose} />;
  }

  if (content.type === "viz_picker") {
    return (
      <LargeVisualizationPicker
        projectId={projectId}
        messageId={content.messageId}
        onClose={onClose}
      />
    );
  }

  return null;
}
