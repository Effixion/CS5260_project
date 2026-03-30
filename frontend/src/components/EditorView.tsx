"use client";

import { useEffect } from "react";
import { TexEditor } from "@/components/TexEditor";
import { PdfCompilerView } from "@/components/PdfCompilerView";
import { EditorChatStrip } from "@/components/EditorChatStrip";
import { useTexEditor } from "@/hooks/useTexEditor";
import { useProject } from "@/contexts/ProjectContext";
import { api } from "@/lib/api";

interface EditorViewProps {
  projectId: string;
}

export function EditorView({ projectId }: EditorViewProps) {
  const editor = useTexEditor({ projectId });
  const { refreshFiles } = useProject();

  // Load tex content on mount
  useEffect(() => {
    editor.loadInitial();
  }, []);  // eslint-disable-line react-hooks/exhaustive-deps

  const handleUploadFiles = async (files: File[]) => {
    try {
      await api.uploadFiles(projectId, files);
      await refreshFiles();
    } catch (err) {
      console.error("Failed to upload files:", err);
    }
  };

  return (
    <div className="flex flex-1 flex-col overflow-hidden">
      {/* Main editor area: tex editor (left) + PDF preview (right) */}
      <div className="flex flex-1 overflow-hidden">
        {/* Left: TeX editor */}
        <div className="flex-1 overflow-hidden border-r border-border">
          <TexEditor
            value={editor.texContent}
            onChange={editor.setTexContent}
            readonly={editor.isEditing}
          />
        </div>

        {/* Right: PDF preview */}
        <div className="flex-1 overflow-hidden">
          <PdfCompilerView
            projectId={projectId}
            pdfUrl={editor.pdfUrl}
            compilationResult={editor.compilationResult}
            isCompiling={editor.isCompiling}
            onCompile={editor.compile}
            pdfTimestamp={editor.pdfTimestamp}
          />
        </div>
      </div>

      {/* Bottom: chat strip */}
      <EditorChatStrip
        onSendInstruction={editor.sendInstruction}
        onUndo={editor.undo}
        onAccept={editor.acceptEdit}
        onUploadFiles={handleUploadFiles}
        canUndo={editor.canUndo}
        hasPendingEdit={editor.pendingAiEdit !== null}
        isEditing={editor.isEditing}
      />
    </div>
  );
}
