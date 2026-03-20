"use client";

import { useState, useRef, useCallback, useEffect } from "react";
import { Send, FileText, X } from "lucide-react";
import { FileAutocomplete } from "@/components/FileAutocomplete";
import { Button } from "@/components/ui/button";
import {
  Tooltip,
  TooltipContent,
  TooltipTrigger,
} from "@/components/ui/tooltip";

interface ChatInputProps {
  onSend: (content: string, fileRefs?: string[]) => void;
  disabled?: boolean;
}

// --- Helpers for the contenteditable editor ---

function createChipElement(
  filename: string,
  onRemove: () => void
): HTMLSpanElement {
  const chip = document.createElement("span");
  chip.contentEditable = "false";
  chip.setAttribute("data-file-ref", filename);
  chip.className =
    "inline-flex items-center gap-1 rounded-md border border-primary/30 bg-primary/10 px-1.5 py-0.5 mx-0.5 text-xs font-medium text-primary align-baseline cursor-default select-none";

  const icon = document.createElement("span");
  icon.className = "flex items-center shrink-0";
  icon.innerHTML = `<svg width="12" height="12" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><path d="M15 2H6a2 2 0 0 0-2 2v16a2 2 0 0 0 2 2h12a2 2 0 0 0 2-2V7Z"/><path d="M14 2v4a2 2 0 0 0 2 2h4"/></svg>`;

  const label = document.createElement("span");
  label.textContent = filename;
  label.className = "truncate";
  label.style.maxWidth = "160px";

  const btn = document.createElement("span");
  btn.className =
    "flex items-center ml-0.5 rounded-sm opacity-50 hover:opacity-100 cursor-pointer";
  btn.innerHTML = `<svg width="10" height="10" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2.5" stroke-linecap="round" stroke-linejoin="round"><path d="M18 6 6 18"/><path d="m6 6 12 12"/></svg>`;
  btn.addEventListener("mousedown", (e) => {
    e.preventDefault();
    e.stopPropagation();
    onRemove();
  });

  chip.append(icon, label, btn);
  return chip;
}

function extractContentAndRefs(editor: HTMLDivElement): {
  content: string;
  refs: string[];
} {
  const refs: string[] = [];
  let content = "";

  const walk = (node: Node) => {
    if (node.nodeType === Node.TEXT_NODE) {
      content += node.textContent || "";
    } else if (node instanceof HTMLElement) {
      const ref = node.getAttribute("data-file-ref");
      if (ref) {
        refs.push(ref);
      } else if (node.tagName === "BR") {
        content += "\n";
      } else {
        node.childNodes.forEach(walk);
      }
    }
  };

  editor.childNodes.forEach(walk);
  content = content.replace(/\u00a0/g, " ").trim();
  return { content, refs };
}

function collectRefsFromDom(editor: HTMLDivElement): string[] {
  return Array.from(editor.querySelectorAll("[data-file-ref]")).map(
    (el) => el.getAttribute("data-file-ref")!
  );
}

// --- Component ---

export function ChatInput({ onSend, disabled }: ChatInputProps) {
  const [isEmpty, setIsEmpty] = useState(true);
  const [attachedRefs, setAttachedRefs] = useState<string[]>([]);
  const [autocomplete, setAutocomplete] = useState<{
    active: boolean;
    query: string;
  }>({ active: false, query: "" });
  const editorRef = useRef<HTMLDivElement>(null);
  const atAnchorRef = useRef<{ node: Node; offset: number } | null>(null);

  // --- Sync isEmpty + attachedRefs from DOM ---
  const syncState = useCallback(() => {
    const el = editorRef.current;
    if (!el) return;
    const text = el.textContent || "";
    const refs = collectRefsFromDom(el);
    setIsEmpty(!text.trim() && refs.length === 0);
    setAttachedRefs(refs);
  }, []);

  // --- @ autocomplete detection ---
  const checkAtTrigger = useCallback(() => {
    const sel = window.getSelection();
    if (!sel || sel.rangeCount === 0 || !editorRef.current) {
      setAutocomplete({ active: false, query: "" });
      return;
    }
    const range = sel.getRangeAt(0);
    const node = range.startContainer;
    if (node.nodeType !== Node.TEXT_NODE) {
      setAutocomplete({ active: false, query: "" });
      return;
    }
    const text = node.textContent || "";
    const cursor = range.startOffset;
    const before = text.slice(0, cursor);
    const atIdx = before.lastIndexOf("@");
    if (atIdx >= 0) {
      const afterAt = before.slice(atIdx + 1);
      const charBefore = atIdx > 0 ? before[atIdx - 1] : " ";
      if (
        (charBefore === " " || charBefore === "\n" || atIdx === 0) &&
        !afterAt.includes(" ")
      ) {
        atAnchorRef.current = { node, offset: atIdx };
        setAutocomplete({ active: true, query: afterAt });
        return;
      }
    }
    setAutocomplete({ active: false, query: "" });
  }, []);

  const handleInput = useCallback(() => {
    syncState();
    checkAtTrigger();
  }, [syncState, checkAtTrigger]);

  // --- Insert chip into editor ---
  const insertChip = useCallback(
    (filename: string) => {
      const editor = editorRef.current;
      const anchor = atAnchorRef.current;
      const sel = window.getSelection();
      if (!editor || !anchor || !sel || sel.rangeCount === 0) return;

      const cursorOffset = sel.getRangeAt(0).startOffset;

      // Delete the @query text
      const delRange = document.createRange();
      delRange.setStart(anchor.node, anchor.offset);
      delRange.setEnd(anchor.node, cursorOffset);
      delRange.deleteContents();

      // Build chip
      const chip = createChipElement(filename, () => {
        chip.remove();
        syncState();
        editor.focus();
      });

      // Insert at anchor position
      const insertRange = document.createRange();
      insertRange.setStart(anchor.node, anchor.offset);
      insertRange.collapse(true);
      insertRange.insertNode(chip);

      // Space after chip + place cursor
      const space = document.createTextNode("\u00a0");
      chip.after(space);
      const newRange = document.createRange();
      newRange.setStartAfter(space);
      newRange.collapse(true);
      sel.removeAllRanges();
      sel.addRange(newRange);

      atAnchorRef.current = null;
      setAutocomplete({ active: false, query: "" });
      syncState();
    },
    [syncState]
  );

  const handleFileSelect = useCallback(
    (filename: string) => {
      insertChip(filename);
      editorRef.current?.focus();
    },
    [insertChip]
  );

  // --- Remove a ref from the top bar ---
  const removeAttachedRef = useCallback(
    (filename: string) => {
      const editor = editorRef.current;
      if (!editor) return;
      // Remove the matching inline chip from the editor DOM
      const chip = editor.querySelector(
        `[data-file-ref="${CSS.escape(filename)}"]`
      );
      if (chip) chip.remove();
      syncState();
      editor.focus();
    },
    [syncState]
  );

  // --- Send ---
  const handleSend = useCallback(() => {
    const editor = editorRef.current;
    if (disabled || !editor) return;

    const { content, refs } = extractContentAndRefs(editor);
    if (!content && refs.length === 0) return;

    onSend(content, refs.length > 0 ? refs : undefined);

    editor.innerHTML = "";
    setIsEmpty(true);
    setAttachedRefs([]);
  }, [disabled, onSend]);

  // --- Key handling ---
  const handleKeyDown = useCallback(
    (e: React.KeyboardEvent) => {
      if (autocomplete.active) return;
      if (e.key === "Enter" && !e.shiftKey) {
        e.preventDefault();
        handleSend();
      }
    },
    [autocomplete.active, handleSend]
  );

  // --- Paste: strip formatting, keep plain text ---
  const handlePaste = useCallback((e: React.ClipboardEvent) => {
    e.preventDefault();
    const text = e.clipboardData.getData("text/plain");
    document.execCommand("insertText", false, text);
  }, []);

  // Focus editor on mount
  useEffect(() => {
    if (!disabled) editorRef.current?.focus();
  }, [disabled]);

  const hasContent = !isEmpty || attachedRefs.length > 0;

  return (
    <div className="relative border-t border-border bg-surface px-4 py-3">
      {autocomplete.active && (
        <FileAutocomplete
          query={autocomplete.query}
          onSelect={handleFileSelect}
          onClose={() =>
            setAutocomplete({ active: false, query: "" })
          }
          anchorRect={editorRef.current?.getBoundingClientRect() ?? null}
        />
      )}

      {/* Attached files summary bar */}
      {attachedRefs.length > 0 && (
        <div className="mb-2 flex flex-wrap gap-1.5">
          {attachedRefs.map((ref) => (
            <span
              key={ref}
              className="inline-flex items-center gap-1 rounded-md border border-border bg-muted px-2 py-1 text-xs font-medium text-foreground"
            >
              <FileText className="h-3 w-3 shrink-0 text-primary" />
              <span className="max-w-50 truncate">{ref}</span>
              <button
                type="button"
                onClick={() => removeAttachedRef(ref)}
                className="ml-0.5 rounded-sm p-0.5 text-muted-foreground transition-colors hover:bg-background hover:text-foreground"
              >
                <X className="h-3 w-3" />
              </button>
            </span>
          ))}
        </div>
      )}

      <div className="flex items-end gap-2">
        <div className="relative flex-1">
          {/* Placeholder */}
          {isEmpty && (
            <div className="pointer-events-none absolute inset-0 flex items-center px-3 text-sm text-muted-foreground">
              {disabled
                ? "Waiting for response..."
                : "Type a message... (use @ to reference files)"}
            </div>
          )}
          <div
            ref={editorRef}
            role="textbox"
            aria-multiline="true"
            contentEditable={!disabled}
            suppressContentEditableWarning
            onInput={handleInput}
            onKeyDown={handleKeyDown}
            onPaste={handlePaste}
            className="max-h-32 min-h-10 resize-none overflow-y-auto rounded-lg border border-input bg-background px-3 py-2 text-sm leading-relaxed text-foreground focus:border-primary focus:outline-none focus:ring-1 focus:ring-ring disabled:opacity-50"
            style={{ whiteSpace: "pre-wrap", wordBreak: "break-word" }}
          />
        </div>
        <Tooltip>
          <TooltipTrigger
            render={
              <Button
                size="icon"
                onClick={handleSend}
                disabled={disabled || !hasContent}
                className="shrink-0"
              >
                <Send className="h-4 w-4" />
              </Button>
            }
          />
          <TooltipContent>Send message</TooltipContent>
        </Tooltip>
      </div>
    </div>
  );
}
