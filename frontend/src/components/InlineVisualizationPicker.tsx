"use client";

import { useState } from "react";
import { Check, Loader2 } from "lucide-react";
import { api, type MessageArtifact } from "@/lib/api";
import { Button } from "@/components/ui/button";

interface InlineVisualizationPickerProps {
  projectId: string;
  messageId: string;
  artifacts: MessageArtifact[];
  confirmed?: boolean;
  selectedItems?: string[];
  isStreaming?: boolean;
  onConfirm: (messageId: string, selected: string[]) => void;
  onViewLarger: (messageId: string) => void;
}

export function InlineVisualizationPicker({
  projectId,
  messageId,
  artifacts,
  confirmed,
  selectedItems,
  isStreaming,
  onConfirm,
  onViewLarger,
}: InlineVisualizationPickerProps) {
  const [selected, setSelected] = useState<Set<string>>(
    new Set(selectedItems || [])
  );
  const [confirming, setConfirming] = useState(false);

  const toggle = (filename: string) => {
    if (confirmed || confirming) return;
    setSelected((prev) => {
      const next = new Set(prev);
      if (next.has(filename)) next.delete(filename);
      else next.add(filename);
      return next;
    });
  };

  const handleConfirm = () => {
    if (confirming || isStreaming) return;
    setConfirming(true);
    onConfirm(messageId, Array.from(selected));
  };

  const isDisabled = confirmed || confirming || isStreaming;

  return (
    <div className="space-y-3">
      <div className="grid grid-cols-2 gap-2 sm:grid-cols-3">
        {artifacts.map((artifact) => {
          const isSelected = selected.has(artifact.filename);
          return (
            <button
              key={artifact.filename}
              onClick={() => toggle(artifact.filename)}
              disabled={!!isDisabled}
              className={`relative overflow-hidden rounded-lg border-2 transition-all ${
                isSelected
                  ? "border-primary ring-2 ring-primary/30"
                  : "border-border hover:border-primary-light"
              } ${isDisabled ? "opacity-75" : ""}`}
            >
              <div className="aspect-[4/3] bg-background">
                <img
                  src={api.getArtifactUrl(projectId, artifact.filename)}
                  alt={artifact.filename}
                  className="h-full w-full object-contain"
                />
              </div>
              {isSelected && (
                <div className="absolute top-1 right-1 flex h-5 w-5 items-center justify-center rounded-full bg-primary text-white">
                  <Check className="h-3 w-3" />
                </div>
              )}
            </button>
          );
        })}
      </div>

      {!confirmed && (
        <div className="flex gap-2">
          <Button
            variant="outline"
            size="sm"
            onClick={() => onViewLarger(messageId)}
            disabled={confirming || !!isStreaming}
          >
            View Larger
          </Button>
          <Button
            size="sm"
            onClick={handleConfirm}
            disabled={selected.size === 0 || confirming || !!isStreaming}
          >
            {confirming ? (
              <>
                <Loader2 className="mr-1 h-3 w-3 animate-spin" />
                Confirming...
              </>
            ) : (
              `Confirm Selection (${selected.size})`
            )}
          </Button>
        </div>
      )}

      {confirmed && (
        <p className="text-xs text-muted-foreground">
          Selected {selectedItems?.length || 0} visualization(s)
        </p>
      )}
    </div>
  );
}
