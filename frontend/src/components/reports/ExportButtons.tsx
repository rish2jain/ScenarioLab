'use client';

import { FileText, FileJson, Download, Presentation } from 'lucide-react';
import { Button } from '@/components/ui/Button';

interface ExportButtonsProps {
  onExport: (format: 'pdf' | 'markdown' | 'json' | 'miro') => void;
  isLoading?: boolean;
}

export function ExportButtons({ onExport, isLoading }: ExportButtonsProps) {
  return (
    <div className="flex flex-wrap gap-3">
      <Button
        variant="secondary"
        size="sm"
        leftIcon={<FileText className="w-4 h-4" />}
        onClick={() => onExport('pdf')}
        isLoading={isLoading}
      >
        Export PDF
      </Button>
      <Button
        variant="secondary"
        size="sm"
        leftIcon={<Download className="w-4 h-4" />}
        onClick={() => onExport('markdown')}
        isLoading={isLoading}
      >
        Markdown
      </Button>
      <Button
        variant="secondary"
        size="sm"
        leftIcon={<FileJson className="w-4 h-4" />}
        onClick={() => onExport('json')}
        isLoading={isLoading}
      >
        JSON
      </Button>
      <Button
        variant="secondary"
        size="sm"
        leftIcon={<Presentation className="w-4 h-4" />}
        onClick={() => onExport('miro')}
        isLoading={isLoading}
      >
        Miro Board
      </Button>
    </div>
  );
}
