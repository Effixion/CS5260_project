"use client";

import { useState, useRef, useCallback } from "react";
import {
  Plus,
  FileText,
  FileSpreadsheet,
  FileImage,
  File,
  Trash2,
  Pencil,
  StickyNote,
  Download,
} from "lucide-react";
import { api, type ProjectFile, type ArtifactFile } from "@/lib/api";
import { useProject } from "@/contexts/ProjectContext";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { ScrollArea } from "@/components/ui/scroll-area";
import { Separator } from "@/components/ui/separator";
import {
  Tooltip,
  TooltipContent,
  TooltipTrigger,
} from "@/components/ui/tooltip";
import {
  ContextMenu,
  ContextMenuContent,
  ContextMenuItem,
  ContextMenuSeparator,
  ContextMenuTrigger,
} from "@/components/ui/context-menu";

function FileIcon({ filename }: { filename: string }) {
  const ext = filename.split(".").pop()?.toLowerCase() || "";
  if (["csv", "tsv", "json", "xlsx", "xls"].includes(ext))
    return <FileSpreadsheet className="h-3.5 w-3.5 shrink-0 text-success" />;
  if (["pdf"].includes(ext))
    return <FileText className="h-3.5 w-3.5 shrink-0 text-error" />;
  if (["svg", "png", "jpg", "jpeg"].includes(ext))
    return <FileImage className="h-3.5 w-3.5 shrink-0 text-primary" />;
  if (["tex"].includes(ext))
    return <FileText className="h-3.5 w-3.5 shrink-0 text-warning" />;
  return <File className="h-3.5 w-3.5 shrink-0 text-muted-foreground" />;
}

function formatBytes(bytes: number): string {
  if (bytes < 1024) return `${bytes} B`;
  if (bytes < 1024 * 1024) return `${(bytes / 1024).toFixed(1)} KB`;
  return `${(bytes / (1024 * 1024)).toFixed(1)} MB`;
}

export function FileSidebar() {
  const { project, files, artifacts, refreshFiles } = useProject();
  const [dragOver, setDragOver] = useState(false);
  const [uploading, setUploading] = useState(false);
  const [editingFile, setEditingFile] = useState<{
    filename: string;
    field: "name" | "note";
    value: string;
  } | null>(null);
  const fileInputRef = useRef<HTMLInputElement>(null);

  const projectId = project?.id;

  const handleUpload = useCallback(
    async (fileList: FileList | File[]) => {
      if (!projectId || uploading) return;
      setUploading(true);
      try {
        const filesArray = Array.from(fileList);
        await api.uploadFiles(projectId, filesArray);
        await refreshFiles();
      } finally {
        setUploading(false);
      }
    },
    [projectId, uploading, refreshFiles]
  );

  const handleDrop = useCallback(
    (e: React.DragEvent) => {
      e.preventDefault();
      setDragOver(false);
      if (e.dataTransfer.files.length > 0) {
        handleUpload(e.dataTransfer.files);
      }
    },
    [handleUpload]
  );

  const handleRename = async () => {
    if (!editingFile || !projectId) return;
    if (editingFile.field === "name" && editingFile.value.trim() && editingFile.value !== editingFile.filename) {
      await api.updateFile(projectId, editingFile.filename, { name: editingFile.value.trim() });
    } else if (editingFile.field === "note") {
      await api.updateFile(projectId, editingFile.filename, { note: editingFile.value });
    }
    setEditingFile(null);
    refreshFiles();
  };

  const handleDelete = async (filename: string) => {
    if (!projectId) return;
    await api.deleteFile(projectId, filename);
    refreshFiles();
  };

  return (
    <aside
      className="relative flex h-full w-60 shrink-0 flex-col border-r border-border bg-surface"
      onDragOver={(e) => {
        e.preventDefault();
        setDragOver(true);
      }}
      onDragLeave={() => setDragOver(false)}
      onDrop={handleDrop}
    >
      {/* Header */}
      <div className="flex items-center justify-between border-b border-border px-3 py-2">
        <span className="text-xs font-semibold uppercase tracking-wider text-muted-foreground">
          Files
        </span>
        <Tooltip>
          <TooltipTrigger
            render={
              <Button
                variant="ghost"
                size="icon-xs"
                onClick={() => fileInputRef.current?.click()}
                disabled={uploading}
              >
                <Plus className="h-4 w-4" />
              </Button>
            }
          />
          <TooltipContent>Upload files</TooltipContent>
        </Tooltip>
        <input
          ref={fileInputRef}
          type="file"
          multiple
          className="hidden"
          onChange={(e) => {
            if (e.target.files) handleUpload(e.target.files);
            e.target.value = "";
          }}
        />
      </div>

      {/* Drag overlay */}
      {dragOver && (
        <div className="absolute inset-0 z-10 flex items-center justify-center rounded border-2 border-dashed border-primary bg-primary/5">
          <p className="text-sm font-medium text-primary">Drop files here</p>
        </div>
      )}

      {/* File lists */}
      <ScrollArea className="flex-1">
        {/* Uploads section */}
        {files.length > 0 && (
          <div className="px-1 pt-2">
            <p className="px-2 pb-1 text-[10px] font-semibold uppercase tracking-wider text-muted-foreground">
              Uploads
            </p>
            {files.map((file) => (
              <ContextMenu key={file.filename}>
                <ContextMenuTrigger>
                  <div className="group flex items-center gap-2 rounded px-2 py-1 hover:bg-background cursor-default">
                    <FileIcon filename={file.filename} />
                    <div className="min-w-0 flex-1">
                      {editingFile?.filename === file.filename && editingFile.field === "name" ? (
                        <Input
                          autoFocus
                          value={editingFile.value}
                          onChange={(e) =>
                            setEditingFile({ ...editingFile, value: e.target.value })
                          }
                          onBlur={handleRename}
                          onKeyDown={(e) => {
                            if (e.key === "Enter") handleRename();
                            if (e.key === "Escape") setEditingFile(null);
                          }}
                          className="h-5 w-full border-primary px-1 text-xs"
                        />
                      ) : (
                        <p className="truncate text-xs text-foreground">{file.filename}</p>
                      )}
                      {editingFile?.filename === file.filename && editingFile.field === "note" ? (
                        <Input
                          autoFocus
                          value={editingFile.value}
                          onChange={(e) =>
                            setEditingFile({ ...editingFile, value: e.target.value })
                          }
                          onBlur={handleRename}
                          onKeyDown={(e) => {
                            if (e.key === "Enter") handleRename();
                            if (e.key === "Escape") setEditingFile(null);
                          }}
                          placeholder="Add a note..."
                          className="mt-0.5 h-5 w-full border-primary px-1 text-[10px]"
                        />
                      ) : file.note ? (
                        <p className="truncate text-[10px] text-muted-foreground">{file.note}</p>
                      ) : null}
                    </div>
                    <span className="shrink-0 text-[10px] text-muted-foreground">
                      {formatBytes(file.size_bytes)}
                    </span>
                  </div>
                </ContextMenuTrigger>
                <ContextMenuContent>
                  <ContextMenuItem
                    onClick={() =>
                      setEditingFile({ filename: file.filename, field: "name", value: file.filename })
                    }
                  >
                    <Pencil className="h-3.5 w-3.5" />
                    Rename
                  </ContextMenuItem>
                  <ContextMenuItem
                    onClick={() =>
                      setEditingFile({ filename: file.filename, field: "note", value: file.note || "" })
                    }
                  >
                    <StickyNote className="h-3.5 w-3.5" />
                    {file.note ? "Edit Note" : "Add Note"}
                  </ContextMenuItem>
                  <ContextMenuSeparator />
                  <ContextMenuItem
                    variant="destructive"
                    onClick={() => handleDelete(file.filename)}
                  >
                    <Trash2 className="h-3.5 w-3.5" />
                    Delete
                  </ContextMenuItem>
                </ContextMenuContent>
              </ContextMenu>
            ))}
          </div>
        )}

        {/* Generated artifacts section */}
        {artifacts.length > 0 && (
          <>
            {files.length > 0 && <Separator className="my-2" />}
            <div className="px-1 pt-1">
              <p className="px-2 pb-1 text-[10px] font-semibold uppercase tracking-wider text-muted-foreground">
                Generated
              </p>
              {artifacts.map((artifact) => (
                <ContextMenu key={artifact.filename}>
                  <ContextMenuTrigger>
                    <div className="group flex items-center gap-2 rounded px-2 py-1 hover:bg-background cursor-default">
                      <FileIcon filename={artifact.filename} />
                      <p className="min-w-0 flex-1 truncate text-xs text-foreground">
                        {artifact.filename}
                      </p>
                      <span className="shrink-0 text-[10px] text-muted-foreground">
                        {formatBytes(artifact.size_bytes)}
                      </span>
                    </div>
                  </ContextMenuTrigger>
                  <ContextMenuContent>
                    <ContextMenuItem
                      onClick={() => {
                        const url = api.getArtifactUrl(projectId!, artifact.filename);
                        const a = document.createElement("a");
                        a.href = url;
                        a.download = artifact.filename;
                        a.click();
                      }}
                    >
                      <Download className="h-3.5 w-3.5" />
                      Download
                    </ContextMenuItem>
                  </ContextMenuContent>
                </ContextMenu>
              ))}
            </div>
          </>
        )}

        {/* Empty state */}
        {files.length === 0 && artifacts.length === 0 && (
          <div className="px-3 py-8 text-center">
            <p className="text-xs text-muted-foreground">
              No files yet. Drag & drop or click + to upload.
            </p>
          </div>
        )}
      </ScrollArea>

      {uploading && (
        <div className="border-t border-border px-3 py-2 text-center text-xs text-muted-foreground">
          Uploading...
        </div>
      )}
    </aside>
  );
}
