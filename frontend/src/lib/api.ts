const API_BASE = process.env.NEXT_PUBLIC_API_URL || "http://localhost:8000";

// --- Types ---

export interface Project {
  id: string;
  name: string;
  created_at: string;
  updated_at: string;
  status: "active" | "completed";
}

export interface ProjectDetail extends Project {
  files: ProjectFile[];
  artifacts: ArtifactFile[];
  message_count: number;
}

export interface ProjectFile {
  filename: string;
  original_name: string;
  size_bytes: number;
  mime_type: string;
  note: string;
  uploaded_at: string;
}

export interface ArtifactFile {
  filename: string;
  size_bytes: number;
}

export interface Message {
  id: string;
  role: "user" | "assistant" | "system";
  content: string;
  content_type: "text" | "visualization_picker" | "artifact" | "status";
  file_refs: string[];
  artifacts: MessageArtifact[];
  metadata: Record<string, unknown>;
  created_at: string;
}

export interface MessageArtifact {
  type: string;
  url: string;
  filename: string;
}

export interface CompilationResult {
  success: boolean;
  errors: string[];
  warnings: string[];
  overfull_boxes: string[];
  pdf_url: string | null;
}

// --- Helpers ---

async function request<T>(path: string, init?: RequestInit): Promise<T> {
  const res = await fetch(`${API_BASE}${path}`, init);
  if (!res.ok) {
    const body = await res.text();
    throw new Error(`API error ${res.status}: ${body}`);
  }
  return res.json() as Promise<T>;
}

// --- Projects ---

export const api = {
  listProjects(): Promise<Project[]> {
    return request("/projects");
  },

  createProject(name?: string): Promise<Project> {
    return request("/projects", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ name: name || "Untitled Presentation" }),
    });
  },

  getProject(id: string): Promise<ProjectDetail> {
    return request(`/projects/${id}`, { cache: "no-store" });
  },

  updateProject(id: string, updates: { name?: string }): Promise<Project> {
    return request(`/projects/${id}`, {
      method: "PATCH",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify(updates),
    });
  },

  async deleteProject(id: string): Promise<void> {
    await fetch(`${API_BASE}/projects/${id}`, { method: "DELETE" });
  },

  // --- Messages ---

  getMessages(projectId: string): Promise<Message[]> {
    return request(`/projects/${projectId}/messages`);
  },

  sendMessageStream(
    projectId: string,
    content: string,
    fileRefs?: string[]
  ): Promise<Response> {
    return fetch(`${API_BASE}/projects/${projectId}/messages`, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ content, file_refs: fileRefs }),
    });
  },

  deleteMessagesAfter(
    projectId: string,
    messageId: string
  ): Promise<{ removed: number }> {
    return request(`/projects/${projectId}/messages/${messageId}/after`, {
      method: "DELETE",
    });
  },

  selectVisualizationsStream(
    projectId: string,
    messageId: string,
    selected: string[]
  ): Promise<Response> {
    return fetch(
      `${API_BASE}/projects/${projectId}/messages/${messageId}/select`,
      {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ selected }),
      }
    );
  },

  // --- Files ---

  listFiles(projectId: string): Promise<ProjectFile[]> {
    return request(`/projects/${projectId}/files`);
  },

  async uploadFiles(projectId: string, files: File[]): Promise<ProjectFile[]> {
    const formData = new FormData();
    files.forEach((f) => formData.append("files", f));
    return request(`/projects/${projectId}/files`, {
      method: "POST",
      body: formData,
    });
  },

  updateFile(
    projectId: string,
    filename: string,
    updates: { name?: string; note?: string }
  ): Promise<ProjectFile> {
    return request(
      `/projects/${projectId}/files/${encodeURIComponent(filename)}`,
      {
        method: "PATCH",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify(updates),
      }
    );
  },

  async deleteFile(projectId: string, filename: string): Promise<void> {
    await fetch(
      `${API_BASE}/projects/${projectId}/files/${encodeURIComponent(filename)}`,
      { method: "DELETE" }
    );
  },

  getFileUrl(projectId: string, filename: string): string {
    return `${API_BASE}/projects/${projectId}/files/${encodeURIComponent(filename)}/download`;
  },

  getArtifactUrl(projectId: string, filename: string): string {
    return `${API_BASE}/projects/${projectId}/artifacts/${encodeURIComponent(filename)}`;
  },

  // --- Editor (Stage 2) ---

  getTexContent(projectId: string): Promise<{ tex_content: string; undo_count: number }> {
    return request(`/projects/${projectId}/tex`);
  },

  saveTex(projectId: string, content: string): Promise<{ success: boolean; version: number }> {
    return request(`/projects/${projectId}/tex`, {
      method: "PUT",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ content }),
    });
  },

  compileTex(
    projectId: string,
    texContent?: string
  ): Promise<CompilationResult> {
    return request(`/projects/${projectId}/compile`, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ tex_content: texContent ?? null }),
    });
  },

  editTexStream(
    projectId: string,
    instruction: string,
    currentTex: string,
    fileRefs?: string[]
  ): Promise<Response> {
    return fetch(`${API_BASE}/projects/${projectId}/edit`, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({
        instruction,
        current_tex: currentTex,
        file_refs: fileRefs,
      }),
    });
  },

  undoTex(projectId: string): Promise<{ tex_content: string; remaining_undos: number }> {
    return request(`/projects/${projectId}/undo`, { method: "POST" });
  },
};
