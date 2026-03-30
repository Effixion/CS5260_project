"use client";

import { use, useState } from "react";
import { useProject } from "@/contexts/ProjectContext";
import { ChatArea } from "@/components/ChatArea";
import { FocusView } from "@/components/FocusView";
import { EditorView } from "@/components/EditorView";

export type FocusContent =
  | null
  | { type: "viz_picker"; messageId: string }
  | { type: "results" };

export default function ProjectPage({
  params,
}: {
  params: Promise<{ id: string }>;
}) {
  const { id } = use(params);
  const { loading, project, artifacts } = useProject();
  const [focusContent, setFocusContent] = useState<FocusContent>(null);

  if (loading) {
    return (
      <div className="flex flex-1 items-center justify-center text-foreground-muted">
        Loading project...
      </div>
    );
  }

  // Auto-transition to editor when presentation.tex is generated and project is completed
  const hasPresentation = artifacts.some((a) => a.filename === "presentation.tex");
  const isCompleted = project?.status === "completed";
  const showEditor = hasPresentation && isCompleted;

  if (showEditor) {
    return <EditorView projectId={id} />;
  }

  return (
    <>
      {focusContent ? (
        <FocusView
          projectId={id}
          content={focusContent}
          onClose={() => setFocusContent(null)}
        />
      ) : (
        <ChatArea
          projectId={id}
          onFocusChange={setFocusContent}
        />
      )}
    </>
  );
}
