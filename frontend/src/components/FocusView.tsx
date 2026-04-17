"use client";

import { ChevronLeft } from "lucide-react";
import { api } from "@/lib/api";
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
  onClose,
}: {
  projectId: string;
  messageId: string;
  onClose: () => void;
}) {
  const { artifacts } = useProject();

  const plotArtifacts = artifacts.filter((a) =>
    a.filename.startsWith("candidate_plot_")
  );

  return (
    <div className="flex flex-1 flex-col overflow-y-auto p-6">
      <div className="mx-auto w-full max-w-5xl space-y-6">
        <div className="flex items-center justify-between">
          <h2 className="text-xl font-semibold text-foreground">
            Visualization Preview
          </h2>
          <Button variant="outline" onClick={onClose}>
            <ChevronLeft className="mr-1 h-4 w-4" />
            Back to Chat
          </Button>
        </div>

        <p className="text-sm text-muted-foreground">
          Preview of the candidate plots. Return to chat to select and confirm.
        </p>

        <div className="grid grid-cols-2 gap-4 lg:grid-cols-3">
          {plotArtifacts.map((artifact) => (
            <div
              key={artifact.filename}
              className="overflow-hidden rounded-lg border-2 border-border"
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
            </div>
          ))}
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
