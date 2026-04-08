"use client";

import { useState, useCallback, useEffect, useRef } from "react";
import { EventSourceParserStream } from "eventsource-parser/stream";
import { api, type Message } from "@/lib/api";
import { useProject } from "@/contexts/ProjectContext";

interface AgentStatus {
  agent: string;
  status: "running" | "completed" | "error";
  usage?: any;
}

interface StreamArtifact {
  type: string;
  url: string;
  filename?: string;
}

interface UseChatStreamReturn {
  messages: Message[];
  isStreaming: boolean;
  agentStatuses: AgentStatus[];
  streamArtifacts: StreamArtifact[];
  projectStatus: string;
  sendMessage: (content: string, fileRefs?: string[]) => Promise<void>;
  selectVisualizations: (messageId: string, selected: string[]) => Promise<void>;
  retryFrom: (messageId: string, newContent?: string) => Promise<void>;
}

export function useChatStream(projectId: string): UseChatStreamReturn {
  const { addSessionCost } = useProject();
  const [messages, setMessages] = useState<Message[]>([]);
  const [isStreaming, setIsStreaming] = useState(false);
  const [agentStatuses, setAgentStatuses] = useState<AgentStatus[]>([]);
  const [streamArtifacts, setStreamArtifacts] = useState<StreamArtifact[]>([]);
  const [projectStatus, setProjectStatus] = useState("active");
  const abortRef = useRef<AbortController | null>(null);

  // Load message history on mount
  useEffect(() => {
    let cancelled = false;
    api.getMessages(projectId).then((msgs) => {
      if (!cancelled) setMessages(msgs);
    });
    return () => {
      cancelled = true;
    };
  }, [projectId]);

  const processSSEStream = useCallback(
    async (response: Response) => {
      if (!response.ok || !response.body) {
        throw new Error(`Stream error: ${response.status}`);
      }

      setIsStreaming(true);
      setAgentStatuses([]);
      setStreamArtifacts([]);

      const stream = response.body
        .pipeThrough(new TextDecoderStream())
        .pipeThrough(new EventSourceParserStream());

      const reader = stream.getReader();

      try {
        while (true) {
          const { done, value } = await reader.read();
          if (done) break;

          const event = value;
          if (!event.data) continue;

          let data: Record<string, unknown>;
          try {
            data = JSON.parse(event.data);
          } catch {
            continue;
          }

          switch (event.event) {
            case "message":
              setMessages((prev) => [...prev, data as unknown as Message]);
              break;

            case "message_delta":
              // Streaming text append to last message
              setMessages((prev) => {
                const updated = [...prev];
                const last = updated[updated.length - 1];
                if (last && last.id === data.message_id) {
                  updated[updated.length - 1] = {
                    ...last,
                    content: last.content + (data.delta as string),
                  };
                }
                return updated;
              });
              break;

            case "agent_status":
              // 1. Define the status up here first
              const status = data as unknown as AgentStatus;

              // 2. Run the math/side-effects OUTSIDE the state updater
              if (status.status === "completed" && status.usage) {
                console.log(`Tokens for ${status.agent}:`, status.usage);
                
                if (typeof status.usage.cost_usd === 'number') {
                  addSessionCost(status.usage.cost_usd);
                } else if (typeof status.usage.cost === 'number') {
                  addSessionCost(status.usage.cost);
                }
              }
              
              setAgentStatuses((prev) => {
                const existing = prev.findIndex(
                  (s) => s.agent === status.agent
                );
                
                if (existing >= 0) {
                  const updated = [...prev];
                  updated[existing] = status;
                  return updated;
                }
                return [...prev, status];
              });
              break;

            case "done":
              setProjectStatus(
                (data.project_status as string) || "active"
              );
              break;

            case "artifact":
              setStreamArtifacts((prev) => [
                ...prev,
                data as unknown as StreamArtifact,
              ]);
              break;

            case "error":
              console.error("SSE error:", data.message);
              break;
          }
        }
      } finally {
        reader.releaseLock();
        setIsStreaming(false);
      }
    },
    [addSessionCost]
  );

  const sendMessage = useCallback(
    async (content: string, fileRefs?: string[]) => {
      if (isStreaming) return;

      // Optimistically add user message
      const optimisticMsg: Message = {
        id: `temp-${Date.now()}`,
        role: "user",
        content,
        content_type: "text",
        file_refs: fileRefs || [],
        artifacts: [],
        metadata: {},
        created_at: new Date().toISOString(),
      };
      setMessages((prev) => [...prev, optimisticMsg]);
      setIsStreaming(true);
      setAgentStatuses([]);

      try {
        abortRef.current = new AbortController();
        const response = await api.sendMessageStream(
          projectId,
          content,
          fileRefs
        );
        await processSSEStream(response);
      } catch (err) {
        console.error("Send message error:", err);
        setIsStreaming(false);
      }
    },
    [projectId, isStreaming, processSSEStream]
  );

  const selectVisualizations = useCallback(
    async (messageId: string, selected: string[]) => {
      if (isStreaming) return;

      // Optimistically mark the visualization picker message as confirmed
      setMessages((prev) =>
        prev.map((m) =>
          m.id === messageId
            ? { ...m, metadata: { ...m.metadata, selected, confirmed: true } }
            : m
        )
      );

      try {
        const response = await api.selectVisualizationsStream(
          projectId,
          messageId,
          selected
        );
        await processSSEStream(response);
      } catch (err) {
        console.error("Select visualizations error:", err);
        setIsStreaming(false);
      }
    },
    [projectId, isStreaming, processSSEStream]
  );

  const retryFrom = useCallback(
    async (messageId: string, newContent?: string) => {
      if (isStreaming) return;

      // Find the message to retry
      const idx = messages.findIndex((m) => m.id === messageId);
      if (idx < 0) return;

      const originalMsg = messages[idx];
      const content = newContent ?? originalMsg.content;
      const fileRefs = originalMsg.file_refs;

      // Delete messages after this one on the backend
      await api.deleteMessagesAfter(projectId, messageId);

      // Also delete the message itself from backend (it will be re-sent)
      // We achieve this by deleting after the previous message
      if (idx > 0) {
        const prevId = messages[idx - 1].id;
        await api.deleteMessagesAfter(projectId, prevId);
      }

      // Truncate local state to before the retried message
      setMessages((prev) => prev.slice(0, idx));

      // Re-send
      const optimisticMsg: Message = {
        id: `temp-${Date.now()}`,
        role: "user",
        content,
        content_type: "text",
        file_refs: fileRefs || [],
        artifacts: [],
        metadata: {},
        created_at: new Date().toISOString(),
      };
      setMessages((prev) => [...prev, optimisticMsg]);
      setIsStreaming(true);
      setAgentStatuses([]);

      try {
        abortRef.current = new AbortController();
        const response = await api.sendMessageStream(
          projectId,
          content,
          fileRefs
        );
        await processSSEStream(response);
      } catch (err) {
        console.error("Retry message error:", err);
        setIsStreaming(false);
      }
    },
    [projectId, isStreaming, messages, processSSEStream]
  );

  return {
    messages,
    isStreaming,
    agentStatuses,
    streamArtifacts,
    projectStatus,
    sendMessage,
    selectVisualizations,
    retryFrom,
  };
}
