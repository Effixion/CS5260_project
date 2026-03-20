"use client";

import { createContext, useContext, useState, useCallback, useEffect, type ReactNode } from "react";
import { api, type ProjectDetail, type ProjectFile, type ArtifactFile } from "@/lib/api";

interface ProjectContextValue {
  project: ProjectDetail | null;
  files: ProjectFile[];
  artifacts: ArtifactFile[];
  loading: boolean;
  refreshProject: () => Promise<void>;
  refreshFiles: () => Promise<void>;
}

const ProjectContext = createContext<ProjectContextValue | null>(null);

export function ProjectProvider({
  projectId,
  children,
}: {
  projectId: string;
  children: ReactNode;
}) {
  const [project, setProject] = useState<ProjectDetail | null>(null);
  const [files, setFiles] = useState<ProjectFile[]>([]);
  const [artifacts, setArtifacts] = useState<ArtifactFile[]>([]);
  const [loading, setLoading] = useState(true);

  const refreshProject = useCallback(async () => {
    try {
      const data = await api.getProject(projectId);
      setProject(data);
      setFiles(data.files);
      setArtifacts(data.artifacts);
    } catch {
      // handle error silently
    } finally {
      setLoading(false);
    }
  }, [projectId]);

  const refreshFiles = useCallback(async () => {
    try {
      const [fileData, projectData] = await Promise.all([
        api.listFiles(projectId),
        api.getProject(projectId),
      ]);
      setFiles(fileData);
      setArtifacts(projectData.artifacts);
    } catch {
      // handle error silently
    }
  }, [projectId]);

  useEffect(() => {
    refreshProject();
  }, [refreshProject]);

  return (
    <ProjectContext.Provider
      value={{ project, files, artifacts, loading, refreshProject, refreshFiles }}
    >
      {children}
    </ProjectContext.Provider>
  );
}

export function useProject() {
  const ctx = useContext(ProjectContext);
  if (!ctx) throw new Error("useProject must be used within ProjectProvider");
  return ctx;
}
