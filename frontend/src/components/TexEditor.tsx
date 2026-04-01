"use client";

import { useEffect, useRef, useCallback } from "react";
import { EditorView, keymap, placeholder } from "@codemirror/view";
import { EditorState, Compartment } from "@codemirror/state";
import { defaultKeymap, history, historyKeymap } from "@codemirror/commands";
import { searchKeymap, highlightSelectionMatches } from "@codemirror/search";
import { bracketMatching, foldGutter, foldKeymap } from "@codemirror/language";
import { oneDark } from "@codemirror/theme-one-dark";
import { lineNumbers, highlightActiveLineGutter, highlightActiveLine } from "@codemirror/view";
import { StreamLanguage } from "@codemirror/language";
import { stex } from "@codemirror/legacy-modes/mode/stex";

interface TexEditorProps {
  value: string;
  onChange: (value: string) => void;
  readonly?: boolean;
}

export function TexEditor({ value, onChange, readonly = false }: TexEditorProps) {
  const containerRef = useRef<HTMLDivElement>(null);
  const viewRef = useRef<EditorView | null>(null);
  const onChangeRef = useRef(onChange);
  onChangeRef.current = onChange;

  const readonlyCompartment = useRef(new Compartment());

  // Track whether the last update was external (from props)
  const isExternalUpdate = useRef(false);

  const createEditor = useCallback(() => {
    if (!containerRef.current) return;

    // Destroy previous instance
    if (viewRef.current) {
      viewRef.current.destroy();
    }

    const updateListener = EditorView.updateListener.of((update) => {
      if (update.docChanged && !isExternalUpdate.current) {
        onChangeRef.current(update.state.doc.toString());
      }
    });

    const state = EditorState.create({
      doc: value,
      extensions: [
        lineNumbers(),
        highlightActiveLineGutter(),
        highlightActiveLine(),
        history(),
        foldGutter(),
        bracketMatching(),
        highlightSelectionMatches(),
        StreamLanguage.define(stex),
        oneDark,
        keymap.of([
          ...defaultKeymap,
          ...historyKeymap,
          ...searchKeymap,
          ...foldKeymap,
        ]),
        placeholder("LaTeX source will appear here..."),
        updateListener,
        readonlyCompartment.current.of(EditorState.readOnly.of(readonly)),
        EditorView.theme({
          "&": { height: "100%", fontSize: "13px" },
          ".cm-scroller": { overflow: "auto" },
          ".cm-content": { fontFamily: "'JetBrains Mono', 'Fira Code', monospace" },
          ".cm-gutters": { fontFamily: "'JetBrains Mono', 'Fira Code', monospace" },
        }),
      ],
    });

    viewRef.current = new EditorView({
      state,
      parent: containerRef.current,
    });
  }, []);  // Only create once

  // Initialize editor
  useEffect(() => {
    createEditor();
    return () => {
      viewRef.current?.destroy();
    };
  }, [createEditor]);

  // Update content when value prop changes externally
  useEffect(() => {
    const view = viewRef.current;
    if (!view) return;

    const currentContent = view.state.doc.toString();
    if (currentContent !== value) {
      isExternalUpdate.current = true;
      view.dispatch({
        changes: {
          from: 0,
          to: currentContent.length,
          insert: value,
        },
      });
      isExternalUpdate.current = false;
    }
  }, [value]);

  // Update readonly state
  useEffect(() => {
    const view = viewRef.current;
    if (!view) return;

    view.dispatch({
      effects: readonlyCompartment.current.reconfigure(
        EditorState.readOnly.of(readonly)
      ),
    });
  }, [readonly]);

  return (
    <div
      ref={containerRef}
      className="h-full w-full overflow-hidden rounded-md border border-border"
    />
  );
}
