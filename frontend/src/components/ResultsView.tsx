"use client";

import { Download, FileText, FileCode, ChevronLeft } from "lucide-react";
import { useProject } from "@/contexts/ProjectContext";
import { api } from "@/lib/api";
import { PdfPreview } from "@/components/PdfPreview";
import { Button } from "@/components/ui/button";
import { Card, CardContent } from "@/components/ui/card";
import { Separator } from "@/components/ui/separator";

interface ResultsViewProps {
  projectId: string;
  onBackToChat: () => void;
}

export function ResultsView({ projectId, onBackToChat }: ResultsViewProps) {
  const { artifacts } = useProject();

  const pdfArtifact = artifacts.find((a) => a.filename.endsWith(".pdf"));
  const texArtifact = artifacts.find(
    (a) => a.filename === "presentation.tex"
  );
  const scriptArtifact = artifacts.find(
    (a) => a.filename === "presenter_script.txt"
  );

  return (
    <div className="flex flex-1 flex-col overflow-y-auto p-6">
      <div className="mx-auto w-full max-w-4xl space-y-6">
        <div className="flex items-center justify-between">
          <h2 className="text-xl font-semibold text-foreground">
            Presentation Preview
          </h2>
          <Button variant="outline" onClick={onBackToChat}>
            <ChevronLeft className="mr-1 h-4 w-4" />
            Back to Chat
          </Button>
        </div>

        {pdfArtifact ? (
          <PdfPreview
            url={api.getArtifactUrl(projectId, pdfArtifact.filename)}
          />
        ) : texArtifact ? (
          <Card>
            <CardContent className="p-4">
              <p className="text-sm text-muted-foreground">
                PDF not available. LaTeX source is ready for download.
              </p>
            </CardContent>
          </Card>
        ) : (
          <Card>
            <CardContent className="p-4">
              <p className="text-sm text-muted-foreground">
                No presentation artifacts found yet.
              </p>
            </CardContent>
          </Card>
        )}

        <Separator />

        <div className="flex flex-wrap gap-3">
          {pdfArtifact && (
            <Button
              render={
                <a
                  href={api.getArtifactUrl(projectId, pdfArtifact.filename)}
                  download
                />
              }
            >
              <Download className="mr-2 h-4 w-4" />
              Download PDF
            </Button>
          )}
          {texArtifact && (
            <Button
              variant="outline"
              render={
                <a
                  href={api.getArtifactUrl(projectId, texArtifact.filename)}
                  download
                />
              }
            >
              <FileCode className="mr-2 h-4 w-4" />
              Download LaTeX
            </Button>
          )}
          {scriptArtifact && (
            <Button
              variant="ghost"
              render={
                <a
                  href={api.getArtifactUrl(projectId, scriptArtifact.filename)}
                  download
                />
              }
            >
              <FileText className="mr-2 h-4 w-4" />
              Download Speaker Notes
            </Button>
          )}
        </div>
      </div>
    </div>
  );
}
