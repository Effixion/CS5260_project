"use client";

import { useState, useEffect, useRef } from "react";
import { FileText } from "lucide-react";
import { useProject } from "@/contexts/ProjectContext";
import { cn } from "@/lib/utils";

interface FileAutocompleteProps {
  query: string;
  onSelect: (filename: string) => void;
  onClose: () => void;
  anchorRect: DOMRect | null;
}

export function FileAutocomplete({
  query,
  onSelect,
  onClose,
  anchorRect,
}: FileAutocompleteProps) {
  const { files } = useProject();
  const [selectedIndex, setSelectedIndex] = useState(0);
  const ref = useRef<HTMLDivElement>(null);

  const filtered = files.filter((f) =>
    f.filename.toLowerCase().includes(query.toLowerCase())
  );

  useEffect(() => {
    setSelectedIndex(0);
  }, [query]);

  useEffect(() => {
    const handleKey = (e: KeyboardEvent) => {
      if (e.key === "ArrowDown") {
        e.preventDefault();
        setSelectedIndex((i) => Math.min(i + 1, filtered.length - 1));
      } else if (e.key === "ArrowUp") {
        e.preventDefault();
        setSelectedIndex((i) => Math.max(i - 1, 0));
      } else if (e.key === "Enter" && filtered.length > 0) {
        e.preventDefault();
        onSelect(filtered[selectedIndex].filename);
      } else if (e.key === "Escape") {
        onClose();
      }
    };
    document.addEventListener("keydown", handleKey);
    return () => document.removeEventListener("keydown", handleKey);
  }, [filtered, selectedIndex, onSelect, onClose]);

  if (filtered.length === 0) return null;

  return (
    <div
      ref={ref}
      className="absolute z-50 max-h-48 w-64 overflow-y-auto rounded-lg border border-border bg-popover p-1 shadow-md ring-1 ring-foreground/10"
      style={{
        bottom: anchorRect ? window.innerHeight - anchorRect.top + 4 : "100%",
        left: anchorRect ? anchorRect.left : 0,
      }}
    >
      {filtered.map((file, i) => (
        <button
          key={file.filename}
          onClick={() => onSelect(file.filename)}
          className={cn(
            "flex w-full items-center gap-2 rounded-md px-2 py-1.5 text-left text-sm",
            i === selectedIndex
              ? "bg-accent text-accent-foreground"
              : "text-foreground hover:bg-accent/50"
          )}
        >
          <FileText className="h-3.5 w-3.5 shrink-0 text-muted-foreground" />
          <span className="truncate">{file.filename}</span>
          <span className="ml-auto shrink-0 text-[10px] text-muted-foreground">
            {(file.size_bytes / 1024).toFixed(1)} KB
          </span>
        </button>
      ))}
    </div>
  );
}
