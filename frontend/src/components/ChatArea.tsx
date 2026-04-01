"use client";

import { useCallback } from "react";
import { useChatStream } from "@/hooks/useChatStream";
import { useProject } from "@/contexts/ProjectContext";
import { MessageList } from "@/components/MessageList";
import { ChatInput } from "@/components/ChatInput";
import type { FocusContent } from "@/app/project/[id]/page";

interface ChatAreaProps {
  projectId: string;
  onFocusChange: (content: FocusContent) => void;
}

export function ChatArea({ projectId, onFocusChange }: ChatAreaProps) {
  const {
    messages,
    isStreaming,
    agentStatuses,
    projectStatus,
    sendMessage,
    selectVisualizations,
    retryFrom,
  } = useChatStream(projectId);
  const { refreshFiles } = useProject();

  const handleSend = useCallback(
    async (content: string, fileRefs?: string[]) => {
      await sendMessage(content, fileRefs);
      // Refresh files in case orchestrator created new artifacts
      refreshFiles();
    },
    [sendMessage, refreshFiles]
  );

  const handleVizConfirm = useCallback(
    async (messageId: string, selected: string[]) => {
      await selectVisualizations(messageId, selected);
      refreshFiles();
    },
    [selectVisualizations, refreshFiles]
  );

  const handleVizViewLarger = useCallback(
    (messageId: string) => {
      onFocusChange({ type: "viz_picker", messageId });
    },
    [onFocusChange]
  );

  const handleRetry = useCallback(
    async (messageId: string, newContent?: string) => {
      await retryFrom(messageId, newContent);
      refreshFiles();
    },
    [retryFrom, refreshFiles]
  );

  return (
    <div className="flex flex-1 flex-col overflow-hidden">
      <MessageList
        projectId={projectId}
        messages={messages}
        isStreaming={isStreaming}
        agentStatuses={agentStatuses}
        onVizConfirm={handleVizConfirm}
        onVizViewLarger={handleVizViewLarger}
        onRetry={handleRetry}
      />
      <ChatInput onSend={handleSend} disabled={isStreaming} />
    </div>
  );
}
