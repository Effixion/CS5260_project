import { Card, CardContent } from "@/components/ui/card";

interface PdfPreviewProps {
  url: string;
}

export function PdfPreview({ url }: PdfPreviewProps) {
  return (
    <Card className="overflow-hidden">
      <CardContent className="p-0">
        <iframe
          src={url}
          className="h-[600px] w-full"
          title="PDF Preview"
        />
      </CardContent>
    </Card>
  );
}
