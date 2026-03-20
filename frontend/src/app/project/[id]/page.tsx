"use client";

import { use, useState } from "react";
import { useProject } from "@/contexts/ProjectContext";
import { ChatArea } from "@/components/ChatArea";
import { FocusView } from "@/components/FocusView";

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
  const { loading } = useProject();
  const [focusContent, setFocusContent] = useState<FocusContent>(null);

  if (loading) {
    return (
      <div className="flex flex-1 items-center justify-center text-foreground-muted">
        Loading project...
      </div>
    );
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
