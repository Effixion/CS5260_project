"use client";

import { useState, useCallback, useRef, useEffect } from "react";
import { api, CompilationResult } from "@/lib/api";
import { EventSourceParserStream } from "eventsource-parser/stream";

interface UseTexEditorOptions {
  projectId: string;
}

export interface UseTexEditorReturn {
  texContent: string;
  setTexContent: (content: string) => void;
  pendingAiEdit: string | null;
  isCompiling: boolean;
  isEditing: boolean;
  compilationResult: CompilationResult | null;
  canUndo: boolean;
  pdfUrl: string | null;
  pdfTimestamp: number;
  compile: () => Promise<void>;
  sendInstruction: (instruction: string, fileRefs?: string[]) => Promise<void>;
  acceptEdit: () => void;
  rejectEdit: () => void;
  undo: () => Promise<void>;
  saveManual: () => Promise<void>;
  loadInitial: () => Promise<void>;
}

export function useTexEditor({ projectId }: UseTexEditorOptions): UseTexEditorReturn {
  const [texContent, setTexContentState] = useState("");
  const [pendingAiEdit, setPendingAiEdit] = useState<string | null>(null);
  const [isCompiling, setIsCompiling] = useState(false);
  const [isEditing, setIsEditing] = useState(false);
  const [compilationResult, setCompilationResult] = useState<CompilationResult | null>(null);
  const [canUndo, setCanUndo] = useState(false);
  const [pdfUrl, setPdfUrl] = useState<string | null>(null);
  const [pdfTimestamp, setPdfTimestamp] = useState(Date.now());

  const texContentRef = useRef(texContent);
  texContentRef.current = texContent;

  // Debounce timer for auto-compile
  const compileTimerRef = useRef<ReturnType<typeof setTimeout> | null>(null);

  const setTexContent = useCallback((content: string) => {
    setTexContentState(content);
    texContentRef.current = content;
  }, []);

  const loadInitial = useCallback(async () => {
    try {
      const data = await api.getTexContent(projectId);
      setTexContent(data.tex_content);
      setCanUndo(data.undo_count > 0);

      // Check if PDF already exists
      const pdfArtifactUrl = api.getArtifactUrl(projectId, "presentation.pdf");
      setPdfUrl(pdfArtifactUrl);
      setPdfTimestamp(Date.now());
    } catch {
      // No tex content yet
    }
  }, [projectId, setTexContent]);

  const compile = useCallback(async () => {
    setIsCompiling(true);
    try {
      const result = await api.compileTex(projectId, texContentRef.current);
      setCompilationResult(result);
      if (result.success && result.pdf_url) {
        setPdfUrl(api.getArtifactUrl(projectId, "presentation.pdf"));
        setPdfTimestamp(Date.now());
      }
    } catch (err) {
      setCompilationResult({
        success: false,
        errors: [String(err)],
        warnings: [],
        overfull_boxes: [],
        pdf_url: null,
      });
    } finally {
      setIsCompiling(false);
    }
  }, [projectId]);

  // Debounced auto-compile on tex changes
  const scheduleCompile = useCallback(() => {
    if (compileTimerRef.current) {
      clearTimeout(compileTimerRef.current);
    }
    compileTimerRef.current = setTimeout(() => {
      compile();
    }, 2000);
  }, [compile]);

  const handleTexChange = useCallback((content: string) => {
    setTexContent(content);
    scheduleCompile();
  }, [setTexContent, scheduleCompile]);

  const sendInstruction = useCallback(async (instruction: string, fileRefs?: string[]) => {
    setIsEditing(true);
    try {
      const response = await api.editTexStream(projectId, instruction, texContentRef.current, fileRefs);
      if (!response.ok) {
        throw new Error(`API error ${response.status}`);
      }

      const stream = response.body!
        .pipeThrough(new TextDecoderStream())
        .pipeThrough(new EventSourceParserStream());

      const reader = stream.getReader();
      while (true) {
        const { done, value } = await reader.read();
        if (done) break;

        const event = value;
        if (event.event === "updated_tex" && event.data) {
          const data = JSON.parse(event.data);
          setPendingAiEdit(data.tex_content);
          // Auto-accept: apply the edit immediately and show in editor
          setTexContent(data.tex_content);
          setCanUndo(true);
        } else if (event.event === "error" && event.data) {
          const data = JSON.parse(event.data);
          console.error("Edit error:", data.message);
        }
      }
    } catch (err) {
      console.error("Failed to edit tex:", err);
    } finally {
      setIsEditing(false);
      // Auto-compile after edit
      compile();
    }
  }, [projectId, setTexContent, compile]);

  const acceptEdit = useCallback(() => {
    if (pendingAiEdit) {
      setTexContent(pendingAiEdit);
      setPendingAiEdit(null);
      compile();
    }
  }, [pendingAiEdit, setTexContent, compile]);

  const rejectEdit = useCallback(async () => {
    setPendingAiEdit(null);
    // Undo to restore the pre-edit version
    try {
      const data = await api.undoTex(projectId);
      setTexContent(data.tex_content);
      setCanUndo(data.remaining_undos > 0);
      compile();
    } catch (err) {
      console.error("Failed to undo:", err);
    }
  }, [projectId, setTexContent, compile]);

  const undo = useCallback(async () => {
    try {
      const data = await api.undoTex(projectId);
      setTexContent(data.tex_content);
      setCanUndo(data.remaining_undos > 0);
      setPendingAiEdit(null);
      compile();
    } catch (err) {
      console.error("Failed to undo:", err);
    }
  }, [projectId, setTexContent, compile]);

  const saveManual = useCallback(async () => {
    try {
      const result = await api.saveTex(projectId, texContentRef.current);
      setCanUndo(true);
    } catch (err) {
      console.error("Failed to save:", err);
    }
  }, [projectId]);

  // Cleanup
  useEffect(() => {
    return () => {
      if (compileTimerRef.current) {
        clearTimeout(compileTimerRef.current);
      }
    };
  }, []);

  return {
    texContent,
    setTexContent: handleTexChange,
    pendingAiEdit,
    isCompiling,
    isEditing,
    compilationResult,
    canUndo,
    pdfUrl,
    pdfTimestamp,
    compile,
    sendInstruction,
    acceptEdit,
    rejectEdit,
    undo,
    saveManual,
    loadInitial,
  };
}
