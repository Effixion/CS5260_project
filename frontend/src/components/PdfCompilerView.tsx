"use client";

import { AlertCircle, CheckCircle2, Loader2, RefreshCw } from "lucide-react";
import { Button } from "@/components/ui/button";
import type { CompilationResult } from "@/lib/api";

interface PdfCompilerViewProps {
  projectId: string;
  pdfUrl: string | null;
  compilationResult: CompilationResult | null;
  isCompiling: boolean;
  onCompile: () => void;
  pdfTimestamp: number;
}

export function PdfCompilerView({
  projectId,
  pdfUrl,
  compilationResult,
  isCompiling,
  onCompile,
  pdfTimestamp,
}: PdfCompilerViewProps) {
  const hasErrors = compilationResult && compilationResult.errors.length > 0;
  const hasWarnings = compilationResult && (compilationResult.warnings.length > 0 || compilationResult.overfull_boxes.length > 0);

  return (
    <div className="flex h-full flex-col">
      {/* Toolbar */}
      <div className="flex items-center gap-2 border-b border-border px-3 py-2">
        <Button
          size="sm"
          variant="outline"
          onClick={onCompile}
          disabled={isCompiling}
          className="gap-1.5"
        >
          {isCompiling ? (
            <Loader2 className="h-3.5 w-3.5 animate-spin" />
          ) : (
            <RefreshCw className="h-3.5 w-3.5" />
          )}
          {isCompiling ? "Compiling..." : "Compile"}
        </Button>

        {compilationResult && !isCompiling && (
          <div className="flex items-center gap-1.5 text-xs">
            {compilationResult.success ? (
              <span className="flex items-center gap-1 text-green-500">
                <CheckCircle2 className="h-3.5 w-3.5" />
                Compiled
              </span>
            ) : (
              <span className="flex items-center gap-1 text-red-500">
                <AlertCircle className="h-3.5 w-3.5" />
                Failed
              </span>
            )}
            {hasWarnings && (
              <span className="text-yellow-500">
                ({(compilationResult.warnings.length + compilationResult.overfull_boxes.length)} warnings)
              </span>
            )}
          </div>
        )}
      </div>

      {/* Error/warning panel */}
      {compilationResult && (hasErrors || hasWarnings) && !isCompiling && (
        <div className="max-h-32 overflow-y-auto border-b border-border bg-muted/50 px-3 py-2 text-xs font-mono">
          {compilationResult.errors.map((e, i) => (
            <div key={`err-${i}`} className="text-red-500">{e}</div>
          ))}
          {compilationResult.overfull_boxes.map((o, i) => (
            <div key={`ovr-${i}`} className="text-yellow-500">{o}</div>
          ))}
          {compilationResult.warnings.map((w, i) => (
            <div key={`wrn-${i}`} className="text-yellow-500">{w}</div>
          ))}
        </div>
      )}

      {/* PDF Preview */}
      <div className="flex-1 bg-muted/30">
        {pdfUrl ? (
          <iframe
            src={`${pdfUrl}?t=${pdfTimestamp}`}
            className="h-full w-full"
            title="PDF Preview"
          />
        ) : (
          <div className="flex h-full items-center justify-center text-muted-foreground text-sm">
            {isCompiling ? "Compiling PDF..." : "Click Compile to generate PDF preview"}
          </div>
        )}
      </div>
    </div>
  );
}
