"use client";

import { createContext, useContext, useState, useCallback, useEffect, type ReactNode } from "react";
import { api, type ProjectDetail, type ProjectFile, type ArtifactFile } from "@/lib/api";

interface ProjectContextValue {
  project: ProjectDetail | null;
  files: ProjectFile[];
  artifacts: ArtifactFile[];
  loading: boolean;
  sessionCost: number;
  addSessionCost: (cost: number) => void;
  refreshProject: () => Promise<void>;
  refreshFiles: () => Promise<void>;
}

// Helper to sum up existing cost from the project's token_usage dictionary
function calculateInitialCost(projectData: any): number {
  // If the backend sends null, an empty dict, or no data, safely return 0
  if (!projectData || !projectData.token_usage || Object.keys(projectData.token_usage).length === 0) {
    return 0;
  }
  
  let total = 0;
  
  // Loop through each agent (e.g., latex_author, strategist)
  Object.values(projectData.token_usage).forEach((usages: any) => {
    if (Array.isArray(usages)) {
      // Loop through every time that agent ran
      usages.forEach((usage: any) => {
        if (usage && typeof usage.cost_usd === 'number') {
          total += usage.cost_usd;
        } else if (usage && typeof usage.cost === 'number') {
          total += usage.cost; // Fallback just in case LiteLLM named it differently
        }
      });
    }
  });
  
  return total;
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
  const [sessionCost, setSessionCost] = useState(0);

  const addSessionCost = useCallback((cost: number) => {
    setSessionCost((prev) => prev + cost);
  }, []);

  const refreshProject = useCallback(async () => {
    try {
      const data = await api.getProject(projectId);
      setProject(data);
      setFiles(data.files);
      setArtifacts(data.artifacts);
      
      // Calculate and set the persisted cost from the backend!
      setSessionCost(calculateInitialCost(data)); 
    } catch (error) {
      console.error("Failed to fetch project:", error);
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
    } catch (error) {
      console.error("Failed to refresh files:", error);
    }
  }, [projectId]);

  useEffect(() => {
    refreshProject();
  }, [refreshProject]);

  return (
    <ProjectContext.Provider
      value={{ 
        project, 
        files, 
        artifacts, 
        loading, 
        sessionCost, 
        addSessionCost, 
        refreshProject, 
        refreshFiles 
      }}
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