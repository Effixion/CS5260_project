"use client";

import { useState, useRef, KeyboardEvent } from "react";
import { Send, Undo2, Check, Loader2, Upload } from "lucide-react";
import { Button } from "@/components/ui/button";
import {
  Tooltip,
  TooltipContent,
  TooltipTrigger,
} from "@/components/ui/tooltip";

interface EditorChatStripProps {
  onSendInstruction: (instruction: string, fileRefs?: string[]) => void;
  onUndo: () => void;
  onAccept: () => void;
  onUploadFiles: (files: File[]) => void;
  canUndo: boolean;
  hasPendingEdit: boolean;
  isEditing: boolean;
  disabled?: boolean;
}

export function EditorChatStrip({
  onSendInstruction,
  onUndo,
  onAccept,
  onUploadFiles,
  canUndo,
  hasPendingEdit,
  isEditing,
  disabled = false,
}: EditorChatStripProps) {
  const [input, setInput] = useState("");
  const fileInputRef = useRef<HTMLInputElement>(null);

  const handleSend = () => {
    const trimmed = input.trim();
    if (!trimmed || disabled || isEditing) return;
    onSendInstruction(trimmed);
    setInput("");
  };

  const handleKeyDown = (e: KeyboardEvent<HTMLInputElement>) => {
    if (e.key === "Enter" && !e.shiftKey) {
      e.preventDefault();
      handleSend();
    }
  };

  const handleFileChange = (e: React.ChangeEvent<HTMLInputElement>) => {
    const files = e.target.files;
    if (files && files.length > 0) {
      onUploadFiles(Array.from(files));
      e.target.value = "";
    }
  };

  return (
    <div className="flex items-center gap-2 border-t border-border bg-background px-3 py-2">
      {/* Undo button */}
      <Tooltip>
        <TooltipTrigger
          render={
            <Button
              size="icon"
              variant="ghost"
              onClick={onUndo}
              disabled={!canUndo || isEditing}
              className="h-8 w-8 shrink-0"
            >
              <Undo2 className="h-4 w-4" />
            </Button>
          }
        />
        <TooltipContent>Undo last change</TooltipContent>
      </Tooltip>

      {/* Accept button */}
      {hasPendingEdit && (
        <Tooltip>
          <TooltipTrigger
            render={
              <Button
                size="icon"
                variant="ghost"
                onClick={onAccept}
                disabled={isEditing}
                className="h-8 w-8 shrink-0 text-green-500 hover:text-green-600"
              >
                <Check className="h-4 w-4" />
              </Button>
            }
          />
          <TooltipContent>Accept change</TooltipContent>
        </Tooltip>
      )}

      {/* Upload button */}
      <Tooltip>
        <TooltipTrigger
          render={
            <Button
              size="icon"
              variant="ghost"
              onClick={() => fileInputRef.current?.click()}
              disabled={isEditing}
              className="h-8 w-8 shrink-0"
            >
              <Upload className="h-4 w-4" />
            </Button>
          }
        />
        <TooltipContent>Upload file</TooltipContent>
      </Tooltip>
      <input
        ref={fileInputRef}
        type="file"
        multiple
        className="hidden"
        onChange={handleFileChange}
      />

      {/* Instruction input */}
      <input
        type="text"
        value={input}
        onChange={(e) => setInput(e.target.value)}
        onKeyDown={handleKeyDown}
        disabled={disabled || isEditing}
        placeholder={
          isEditing
            ? "Applying changes..."
            : "Type an instruction to edit the presentation..."
        }
        className="flex-1 rounded-md border border-border bg-muted/50 px-3 py-1.5 text-sm outline-none placeholder:text-muted-foreground focus:border-primary"
      />

      {/* Send button */}
      <Tooltip>
        <TooltipTrigger
          render={
            <Button
              size="icon"
              variant="ghost"
              onClick={handleSend}
              disabled={!input.trim() || disabled || isEditing}
              className="h-8 w-8 shrink-0"
            >
              {isEditing ? (
                <Loader2 className="h-4 w-4 animate-spin" />
              ) : (
                <Send className="h-4 w-4" />
              )}
            </Button>
          }
        />
        <TooltipContent>Send instruction</TooltipContent>
      </Tooltip>
    </div>
  );
}
