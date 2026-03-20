"use client";

import { useEffect, useRef, useState } from "react";
import { FileText, Download, Loader2, Check, RotateCcw, Pencil } from "lucide-react";
import { api, type Message } from "@/lib/api";
import { InlineVisualizationPicker } from "@/components/InlineVisualizationPicker";
import { Badge } from "@/components/ui/badge";
import { Card, CardContent } from "@/components/ui/card";
import {
  ContextMenu,
  ContextMenuContent,
  ContextMenuItem,
  ContextMenuTrigger,
} from "@/components/ui/context-menu";
import { motion, AnimatePresence } from "framer-motion";

interface StreamArtifact {
  type: string;
  url: string;
  filename?: string;
}

interface MessageListProps {
  projectId: string;
  messages: Message[];
  isStreaming: boolean;
  agentStatuses: { agent: string; status: string }[];
  streamArtifacts: StreamArtifact[];
  onVizConfirm: (messageId: string, selected: string[]) => void;
  onVizViewLarger: (messageId: string) => void;
  onRetry: (messageId: string, newContent?: string) => void;
}

function FileRefChip({ filename }: { filename: string }) {
  return (
    <span className="inline-flex items-center gap-1 rounded-md border border-white/20 bg-white/15 px-2 py-0.5 text-xs font-medium backdrop-blur-sm">
      <FileText className="h-3 w-3 shrink-0 opacity-70" />
      <span className="truncate max-w-[150px]">{filename}</span>
    </span>
  );
}

function ArtifactCard({
  projectId,
  artifact,
}: {
  projectId: string;
  artifact: { type: string; url: string; filename: string };
}) {
  const url = api.getArtifactUrl(projectId, artifact.filename);
  return (
    <a
      href={url}
      target="_blank"
      rel="noopener noreferrer"
      className="inline-block"
    >
      <Card className="transition-colors hover:border-primary-light">
        <CardContent className="flex items-center gap-2 px-3 py-2">
          <Download className="h-4 w-4 text-primary" />
          <span className="text-sm text-foreground">{artifact.filename}</span>
          <span className="text-xs text-muted-foreground">{artifact.type}</span>
        </CardContent>
      </Card>
    </a>
  );
}

function EditableUserMessage({
  msg,
  onSubmit,
  onCancel,
}: {
  msg: Message;
  onSubmit: (content: string) => void;
  onCancel: () => void;
}) {
  const [value, setValue] = useState(msg.content);
  const textareaRef = useRef<HTMLTextAreaElement>(null);

  useEffect(() => {
    textareaRef.current?.focus();
    textareaRef.current?.select();
  }, []);

  const handleKeyDown = (e: React.KeyboardEvent) => {
    if (e.key === "Enter" && !e.shiftKey) {
      e.preventDefault();
      if (value.trim()) onSubmit(value.trim());
    }
    if (e.key === "Escape") onCancel();
  };

  return (
    <div className="flex max-w-lg flex-col gap-2">
      <textarea
        ref={textareaRef}
        value={value}
        onChange={(e) => setValue(e.target.value)}
        onKeyDown={handleKeyDown}
        className="min-h-[60px] w-full resize-none rounded-lg border border-primary bg-primary/10 px-4 py-3 text-sm text-foreground outline-none focus:ring-2 focus:ring-primary/30"
        rows={Math.min(value.split("\n").length + 1, 6)}
      />
      <div className="flex justify-end gap-2">
        <button
          onClick={onCancel}
          className="rounded px-3 py-1 text-xs text-muted-foreground hover:text-foreground"
        >
          Cancel
        </button>
        <button
          onClick={() => value.trim() && onSubmit(value.trim())}
          disabled={!value.trim()}
          className="rounded bg-primary px-3 py-1 text-xs text-primary-foreground disabled:opacity-50"
        >
          Send
        </button>
      </div>
    </div>
  );
}

const messageVariants = {
  hidden: { opacity: 0, y: 6 },
  visible: { opacity: 1, y: 0, transition: { duration: 0.2, ease: "easeOut" as const } },
};

export function MessageList({
  projectId,
  messages,
  isStreaming,
  agentStatuses,
  streamArtifacts,
  onVizConfirm,
  onVizViewLarger,
  onRetry,
}: MessageListProps) {
  const bottomRef = useRef<HTMLDivElement>(null);
  const [editingId, setEditingId] = useState<string | null>(null);

  useEffect(() => {
    bottomRef.current?.scrollIntoView({ behavior: "smooth" });
  }, [messages, agentStatuses]);

  return (
    <div className="flex-1 overflow-y-auto">
      <div className="px-4 py-6">
        <div className="mx-auto max-w-2xl space-y-4">
          <AnimatePresence initial={false}>
            {messages.map((msg) => {
              // Status messages — centered indicator
              if (msg.content_type === "status") {
                return (
                  <motion.div
                    key={msg.id}
                    variants={messageVariants}
                    initial="hidden"
                    animate="visible"
                    className="flex justify-center"
                  >
                    <Badge variant="outline" className="gap-2 px-4 py-1.5">
                      {isStreaming && (
                        <Loader2 className="h-3 w-3 animate-spin" />
                      )}
                      {msg.content}
                    </Badge>
                  </motion.div>
                );
              }

              // Visualization picker message
              if (msg.content_type === "visualization_picker") {
                const confirmed = msg.metadata?.confirmed === true;
                const selectedItems = (msg.metadata?.selected as string[]) || [];
                return (
                  <motion.div
                    key={msg.id}
                    variants={messageVariants}
                    initial="hidden"
                    animate="visible"
                    className="flex justify-start"
                  >
                    <Card className="max-w-lg">
                      <CardContent className="p-3">
                        <InlineVisualizationPicker
                          projectId={projectId}
                          messageId={msg.id}
                          artifacts={msg.artifacts}
                          confirmed={confirmed}
                          selectedItems={selectedItems}
                          isStreaming={isStreaming}
                          onConfirm={onVizConfirm}
                          onViewLarger={onVizViewLarger}
                        />
                      </CardContent>
                    </Card>
                  </motion.div>
                );
              }

              // Artifact message
              if (msg.content_type === "artifact") {
                return (
                  <motion.div
                    key={msg.id}
                    variants={messageVariants}
                    initial="hidden"
                    animate="visible"
                    className="flex justify-start"
                  >
                    <div className="max-w-lg space-y-2">
                      {msg.content && (
                        <Card>
                          <CardContent className="px-4 py-3 text-sm text-foreground">
                            {msg.content}
                          </CardContent>
                        </Card>
                      )}
                      <div className="flex flex-wrap gap-2">
                        {msg.artifacts.map((a) => (
                          <ArtifactCard
                            key={a.filename}
                            projectId={projectId}
                            artifact={a}
                          />
                        ))}
                      </div>
                    </div>
                  </motion.div>
                );
              }

              // Regular text messages
              const isUser = msg.role === "user";

              // Editing mode for user messages
              if (isUser && editingId === msg.id) {
                return (
                  <motion.div
                    key={msg.id}
                    variants={messageVariants}
                    initial="hidden"
                    animate="visible"
                    className="flex justify-end"
                  >
                    <EditableUserMessage
                      msg={msg}
                      onSubmit={(content) => {
                        setEditingId(null);
                        onRetry(msg.id, content);
                      }}
                      onCancel={() => setEditingId(null)}
                    />
                  </motion.div>
                );
              }

              // User messages get a context menu
              if (isUser && !isStreaming) {
                return (
                  <motion.div
                    key={msg.id}
                    variants={messageVariants}
                    initial="hidden"
                    animate="visible"
                    className="flex justify-end"
                  >
                    <ContextMenu>
                      <ContextMenuTrigger className="max-w-lg cursor-context-menu rounded-lg bg-primary px-4 py-3 text-sm text-primary-foreground">
                          {msg.file_refs.length > 0 && (
                            <div className="mb-2 flex flex-wrap gap-1">
                              {msg.file_refs.map((ref) => (
                                <FileRefChip key={ref} filename={ref} />
                              ))}
                            </div>
                          )}
                          <p className="whitespace-pre-wrap">{msg.content}</p>
                      </ContextMenuTrigger>
                      <ContextMenuContent>
                        <ContextMenuItem onClick={() => onRetry(msg.id)}>
                          <RotateCcw className="mr-2 h-3.5 w-3.5" />
                          Retry
                        </ContextMenuItem>
                        <ContextMenuItem onClick={() => setEditingId(msg.id)}>
                          <Pencil className="mr-2 h-3.5 w-3.5" />
                          Edit & Resend
                        </ContextMenuItem>
                      </ContextMenuContent>
                    </ContextMenu>
                  </motion.div>
                );
              }

              // Assistant messages (no context menu)
              return (
                <motion.div
                  key={msg.id}
                  variants={messageVariants}
                  initial="hidden"
                  animate="visible"
                  className={`flex ${isUser ? "justify-end" : "justify-start"}`}
                >
                  <div
                    className={`max-w-lg rounded-lg px-4 py-3 text-sm ${
                      isUser
                        ? "bg-primary text-primary-foreground"
                        : "border border-border bg-surface text-foreground"
                    }`}
                  >
                    {msg.file_refs.length > 0 && (
                      <div className="mb-2 flex flex-wrap gap-1">
                        {msg.file_refs.map((ref) => (
                          <FileRefChip key={ref} filename={ref} />
                        ))}
                      </div>
                    )}
                    <p className="whitespace-pre-wrap">{msg.content}</p>
                  </div>
                </motion.div>
              );
            })}
          </AnimatePresence>

          {/* Thinking indicator — shown before any agent statuses arrive */}
          {isStreaming && agentStatuses.length === 0 && (
            <motion.div
              initial={{ opacity: 0 }}
              animate={{ opacity: 1 }}
              className="flex justify-start"
            >
              <div className="flex items-center gap-2 rounded-lg border border-border bg-surface px-4 py-3">
                <Loader2 className="h-3.5 w-3.5 animate-spin text-primary" />
                <span className="text-sm text-muted-foreground">Thinking...</span>
              </div>
            </motion.div>
          )}

          {/* Agent status indicators during streaming */}
          {isStreaming && agentStatuses.length > 0 && (
            <motion.div
              initial={{ opacity: 0 }}
              animate={{ opacity: 1 }}
              className="flex justify-center"
            >
              <Card>
                <CardContent className="space-y-1 px-4 py-2">
                  {agentStatuses.map((s) => (
                    <div key={s.agent} className="flex items-center gap-2 text-xs">
                      {s.status === "running" ? (
                        <Loader2 className="h-2.5 w-2.5 animate-spin text-primary" />
                      ) : s.status === "completed" ? (
                        <Check className="h-2.5 w-2.5 text-success" />
                      ) : (
                        <div className="h-2.5 w-2.5 rounded-full bg-error" />
                      )}
                      <span className="text-muted-foreground capitalize">
                        {s.agent.replace("_", " ")}
                      </span>
                    </div>
                  ))}
                </CardContent>
              </Card>
            </motion.div>
          )}

          {/* Artifact downloads — shown when streaming produces artifacts */}
          {streamArtifacts.length > 0 && !isStreaming && (
            <motion.div
              initial={{ opacity: 0, y: 6 }}
              animate={{ opacity: 1, y: 0 }}
              className="flex justify-start"
            >
              <Card>
                <CardContent className="px-4 py-3">
                  <p className="mb-2 text-xs font-medium text-muted-foreground">Generated Files</p>
                  <div className="flex flex-wrap gap-2">
                    {streamArtifacts.map((a) => (
                      <a
                        key={a.filename || a.url}
                        href={api.getArtifactUrl(projectId, a.filename || "")}
                        target="_blank"
                        rel="noopener noreferrer"
                        className="inline-flex items-center gap-1.5 rounded-md border border-border bg-surface px-3 py-1.5 text-xs text-foreground transition-colors hover:border-primary hover:text-primary"
                      >
                        <Download className="h-3 w-3" />
                        {a.filename || a.type}
                      </a>
                    ))}
                  </div>
                </CardContent>
              </Card>
            </motion.div>
          )}

          <div ref={bottomRef} />
        </div>
      </div>
    </div>
  );
}
