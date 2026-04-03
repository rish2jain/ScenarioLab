'use client';

import { useEffect } from 'react';
import Link from 'next/link';
import { useRouter } from 'next/navigation';
import { FileText, Download, ChevronRight, Calendar } from 'lucide-react';
import { Card } from '@/components/ui/Card';
import { Button } from '@/components/ui/Button';
import { EmptyState } from '@/components/ui/EmptyState';
import { useReportStore } from '@/lib/store';
import { api } from '@/lib/api';

export default function ReportsPage() {
  const router = useRouter();
  const { reports, setReports, setLoading, setError } = useReportStore();

  useEffect(() => {
    const loadReports = async () => {
      setLoading(true);
      try {
        const data = await api.getReports();
        setReports(data);
      } catch (error) {
        const message = error instanceof Error ? error.message : 'Failed to load reports';
        setError(message);
      } finally {
        setLoading(false);
      }
    };

    loadReports();
  }, [setReports, setLoading, setError]);

  const formatDate = (dateString: string) => {
    return new Date(dateString).toLocaleDateString('en-US', {
      month: 'long',
      day: 'numeric',
      year: 'numeric',
    });
  };

  return (
    <div className="space-y-4 md:space-y-6 animate-fade-in">
      {/* Header */}
      <div>
        <h1 className="text-2xl sm:text-3xl font-bold text-slate-100">Reports</h1>
        <p className="text-slate-400 mt-1 text-sm sm:text-base">
          View and export simulation analysis reports
        </p>
      </div>

      {/* Reports List */}
      {reports.length > 0 ? (
        <div className="grid grid-cols-1 gap-4">
          {reports.map((report) => (
            <Card key={report.id} hover className="group">
              <div className="p-4 md:p-6 flex flex-col sm:flex-row sm:items-center justify-between gap-4">
                <div className="flex items-start gap-3 md:gap-4">
                  <div className="w-10 h-10 md:w-12 md:h-12 rounded-xl bg-accent/20 flex items-center justify-center flex-shrink-0">
                    <FileText className="w-5 h-5 md:w-6 md:h-6 text-accent" />
                  </div>
                  <div className="min-w-0">
                    <h3 className="font-semibold text-slate-100 group-hover:text-accent transition-colors truncate">
                      {report.simulationName}
                    </h3>
                    <p className="text-xs md:text-sm text-slate-400 mt-1">
                      Report ID: {report.id}
                    </p>
                    <div className="flex items-center gap-2 mt-2 text-xs text-slate-500">
                      <Calendar className="w-3.5 h-3.5" />
                      <span>Generated on {formatDate(report.generatedAt)}</span>
                    </div>
                  </div>
                </div>
                <div className="flex items-center gap-3">
                  <Link href={`/simulations/${report.simulationId}/report`} className="w-full sm:w-auto">
                    <Button variant="secondary" size="sm" className="w-full sm:w-auto">
                      View Report
                    </Button>
                  </Link>
                </div>
              </div>
            </Card>
          ))}
        </div>
      ) : (
        <Card>
          <EmptyState
            title="No reports yet"
            description="Complete a simulation to generate an analysis report"
            icon={<FileText className="w-8 h-8" />}
            action={{
              label: 'View Simulations',
              onClick: () => router.push('/simulations'),
            }}
          />
        </Card>
      )}
    </div>
  );
}
