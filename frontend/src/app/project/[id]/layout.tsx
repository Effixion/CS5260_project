"use client";

import { use } from "react";
import { ProjectProvider } from "@/contexts/ProjectContext";
import { TopBar } from "@/components/TopBar";
import { FileSidebar } from "@/components/FileSidebar";

export default function ProjectLayout({
  children,
  params,
}: {
  children: React.ReactNode;
  params: Promise<{ id: string }>;
}) {
  const { id } = use(params);

  return (
    <ProjectProvider projectId={id}>
      <div className="flex h-screen flex-col">
        <TopBar />
        <div className="flex flex-1 overflow-hidden">
          <FileSidebar />
          <main className="flex flex-1 flex-col overflow-hidden">
            {children}
          </main>
        </div>
      </div>
    </ProjectProvider>
  );
}
