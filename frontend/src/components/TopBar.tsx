"use client";

import { useState, useRef, useEffect } from "react";
import { useRouter } from "next/navigation";
import { ChevronLeft } from "lucide-react";
import { api } from "@/lib/api";
import { useProject } from "@/contexts/ProjectContext";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Separator } from "@/components/ui/separator";
import {
  Tooltip,
  TooltipContent,
  TooltipTrigger,
} from "@/components/ui/tooltip";

export function TopBar() {
  const { project, refreshProject, sessionCost } = useProject();
  const router = useRouter();
  const [editing, setEditing] = useState(false);
  const [name, setName] = useState("");
  const inputRef = useRef<HTMLInputElement>(null);

  useEffect(() => {
    if (editing && inputRef.current) {
      inputRef.current.focus();
      inputRef.current.select();
    }
  }, [editing]);

  const handleStartEdit = () => {
    setName(project?.name || "");
    setEditing(true);
  };

  const handleSave = async () => {
    setEditing(false);
    if (!project || name.trim() === project.name || !name.trim()) return;
    await api.updateProject(project.id, { name: name.trim() });
    refreshProject();
  };

  return (
    <div className="flex h-12 shrink-0 items-center border-b border-border bg-surface px-4">
      <Button
        variant="ghost"
        size="sm"
        onClick={() => router.push("/")}
        className="mr-3 gap-1.5 text-muted-foreground hover:text-foreground"
      >
        <ChevronLeft className="h-4 w-4" />
        Projects
      </Button>

      <Separator orientation="vertical" className="h-5" />

      {editing ? (
        <Input
          ref={inputRef}
          value={name}
          onChange={(e) => setName(e.target.value)}
          onBlur={handleSave}
          onKeyDown={(e) => {
            if (e.key === "Enter") handleSave();
            if (e.key === "Escape") setEditing(false);
          }}
          className="ml-3 h-7 w-auto max-w-xs border-primary bg-background text-sm font-medium"
        />
      ) : (
        <Tooltip>
          <TooltipTrigger
            render={
              <button
                onClick={handleStartEdit}
                className="ml-3 rounded px-2 py-0.5 text-sm font-medium text-foreground transition-colors hover:bg-background"
              >
                {project?.name || "Loading..."}
              </button>
            }
          />
          <TooltipContent>Click to rename</TooltipContent>
        </Tooltip>
      )}

      {/* The Cost Badge - ml-auto pushes it to the right */}
      <div className="ml-auto flex items-center bg-green-50 border border-green-200 text-green-700 px-3 py-1 rounded-full text-xs font-mono font-medium shadow-sm">
        <span>Token Cost: USD${sessionCost.toFixed(3)}</span>
      </div>
    </div>
  );
}
