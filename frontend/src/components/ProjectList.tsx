"use client";

import { useState, useEffect, useCallback } from "react";
import { useRouter } from "next/navigation";
import { Plus, Trash2 } from "lucide-react";
import { api, type Project } from "@/lib/api";
import { Button } from "@/components/ui/button";
import { Card, CardContent } from "@/components/ui/card";
import { Badge } from "@/components/ui/badge";
import {
  Dialog,
  DialogContent,
  DialogHeader,
  DialogTitle,
  DialogDescription,
  DialogFooter,
} from "@/components/ui/dialog";
import { motion } from "framer-motion";

function timeAgo(dateStr: string): string {
  const now = new Date();
  const date = new Date(dateStr);
  const seconds = Math.floor((now.getTime() - date.getTime()) / 1000);

  if (seconds < 60) return "just now";
  const minutes = Math.floor(seconds / 60);
  if (minutes < 60) return `${minutes}m ago`;
  const hours = Math.floor(minutes / 60);
  if (hours < 24) return `${hours}h ago`;
  const days = Math.floor(hours / 24);
  if (days < 30) return `${days}d ago`;
  return date.toLocaleDateString();
}

const cardVariants = {
  hidden: { opacity: 0, y: 12 },
  visible: (i: number) => ({
    opacity: 1,
    y: 0,
    transition: { delay: i * 0.05, duration: 0.25, ease: "easeOut" as const },
  }),
};

export function ProjectList() {
  const [projects, setProjects] = useState<Project[]>([]);
  const [loading, setLoading] = useState(true);
  const [creating, setCreating] = useState(false);
  const [deleteId, setDeleteId] = useState<string | null>(null);
  const router = useRouter();

  const fetchProjects = useCallback(async () => {
    try {
      const data = await api.listProjects();
      setProjects(data);
    } catch {
      // silently fail — user sees empty state
    } finally {
      setLoading(false);
    }
  }, []);

  useEffect(() => {
    fetchProjects();
  }, [fetchProjects]);

  const handleCreate = async () => {
    if (creating) return;
    setCreating(true);
    try {
      const project = await api.createProject();
      router.push(`/project/${project.id}`);
    } catch {
      setCreating(false);
    }
  };

  const handleDelete = async (id: string) => {
    try {
      await api.deleteProject(id);
      setProjects((prev) => prev.filter((p) => p.id !== id));
    } finally {
      setDeleteId(null);
    }
  };

  return (
    <div className="mx-auto max-w-5xl px-6 py-10">
      {/* Header */}
      <div className="mb-8 flex items-center justify-between">
        <div>
          <h1 className="text-3xl font-bold text-foreground">Haitham</h1>
          <p className="mt-1 text-muted-foreground">
            AI-powered academic presentation generator
          </p>
        </div>
        <Button onClick={handleCreate} disabled={creating}>
          <Plus className="mr-2 h-4 w-4" />
          {creating ? "Creating..." : "New Project"}
        </Button>
      </div>

      {/* Project Grid */}
      {loading ? (
        <div className="py-20 text-center text-muted-foreground">
          Loading projects...
        </div>
      ) : projects.length === 0 ? (
        <div className="py-20 text-center">
          <p className="text-lg text-muted-foreground">No projects yet</p>
          <p className="mt-2 text-sm text-muted-foreground">
            Create your first presentation to get started.
          </p>
        </div>
      ) : (
        <div className="grid grid-cols-1 gap-4 sm:grid-cols-2 lg:grid-cols-3">
          {projects.map((project, i) => (
            <motion.div
              key={project.id}
              custom={i}
              variants={cardVariants}
              initial="hidden"
              animate="visible"
            >
              <Card
                className="group cursor-pointer transition-all hover:border-primary-light hover:shadow-md"
                onClick={() => router.push(`/project/${project.id}`)}
              >
                <CardContent className="p-5">
                  <div className="flex items-start justify-between">
                    <h3 className="font-medium text-foreground group-hover:text-primary">
                      {project.name}
                    </h3>
                    <Badge
                      variant={project.status === "completed" ? "default" : "secondary"}
                      className={
                        project.status === "completed"
                          ? "bg-success/10 text-success hover:bg-success/10"
                          : "bg-primary/10 text-primary hover:bg-primary/10"
                      }
                    >
                      {project.status}
                    </Badge>
                  </div>
                  <p className="mt-2 text-xs text-muted-foreground">
                    Updated {timeAgo(project.updated_at)}
                  </p>
                  <div className="mt-3 flex justify-end">
                    <Button
                      variant="ghost"
                      size="xs"
                      className="opacity-0 transition-opacity group-hover:opacity-100 text-muted-foreground hover:text-destructive"
                      onClick={(e) => {
                        e.stopPropagation();
                        setDeleteId(project.id);
                      }}
                    >
                      <Trash2 className="mr-1 h-3 w-3" />
                      Delete
                    </Button>
                  </div>
                </CardContent>
              </Card>
            </motion.div>
          ))}
        </div>
      )}

      {/* Delete Confirmation Dialog */}
      <Dialog open={!!deleteId} onOpenChange={(open) => !open && setDeleteId(null)}>
        <DialogContent>
          <DialogHeader>
            <DialogTitle>Delete project?</DialogTitle>
            <DialogDescription>
              This action cannot be undone. All files and chat history will be
              permanently deleted.
            </DialogDescription>
          </DialogHeader>
          <DialogFooter>
            <Button variant="outline" onClick={() => setDeleteId(null)}>
              Cancel
            </Button>
            <Button
              variant="destructive"
              onClick={() => deleteId && handleDelete(deleteId)}
            >
              Delete
            </Button>
          </DialogFooter>
        </DialogContent>
      </Dialog>
    </div>
  );
}
