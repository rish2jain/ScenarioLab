'use client';

import { useEffect, useState } from 'react';
import { useParams } from 'next/navigation';
import Link from 'next/link';
import { ChevronLeft, Download, Lightbulb } from 'lucide-react';
import { Card } from '@/components/ui/Card';
import { Button } from '@/components/ui/Button';
import { Tabs } from '@/components/ui/Tabs';
import { ExportButtons } from '@/components/reports/ExportButtons';
import { RiskRegisterTable } from '@/components/reports/RiskRegisterTable';
import { ScenarioMatrixGrid } from '@/components/reports/ScenarioMatrixGrid';
import { StakeholderHeatmap } from '@/components/reports/StakeholderHeatmap';
import { useReportStore } from '@/lib/store';
import { api } from '@/lib/api';
import type { Report } from '@/lib/types';

export default function ReportPage() {
  const params = useParams();
  const rawId = params.id;
  const simulationId = Array.isArray(rawId) ? rawId[0] : rawId ?? '';
  
  const { currentReport, setCurrentReport } = useReportStore();
  const [isLoading, setIsLoading] = useState(true);
  const [isExporting, setIsExporting] = useState(false);

  useEffect(() => {
    const loadReport = async () => {
      setIsLoading(true);
      const data = await api.getReport(simulationId);
      if (data) {
        setCurrentReport(data);
      }
      setIsLoading(false);
    };

    loadReport();
  }, [simulationId, setCurrentReport]);

  const handleExport = async (format: 'pdf' | 'markdown' | 'json' | 'miro') => {
    if (!currentReport) return;
    setIsExporting(true);
    try {
      const result = await api.exportReport(currentReport.id, format);

      if (format === 'miro' && typeof result === 'object' && result !== null) {
        const miroResult = result as {
          mock_mode?: boolean;
          board_url?: string;
          message?: string;
          board_structure?: unknown;
        };

        if (miroResult.mock_mode) {
          // Show mock mode notification with board structure preview
          alert(
            `Miro Export (Mock Mode)\n\n` +
            `${miroResult.message || 'No API token configured'}\n\n` +
            `Board structure preview available in console.`
          );
        } else if (miroResult.board_url) {
          // Real export succeeded - open board URL
          alert(`Miro board created successfully!\n\nOpening: ${miroResult.board_url}`);
          window.open(miroResult.board_url, '_blank');
        }
      } else {
        // For other formats, trigger download
        alert(`Exporting as ${format.toUpperCase()}...`);
      }
    } catch (error) {
      console.error('Export failed:', error);
      alert(`Export failed: ${error instanceof Error ? error.message : 'Unknown error'}`);
    } finally {
      setIsExporting(false);
    }
  };

  if (isLoading) {
    return (
      <div className="flex items-center justify-center h-96">
        <div className="text-slate-400">Loading report...</div>
      </div>
    );
  }

  if (!currentReport) {
    return (
      <div className="flex items-center justify-center h-96">
        <div className="text-slate-400">Report not found</div>
      </div>
    );
  }

  const tabs = [
    {
      id: 'summary',
      label: 'Executive Summary',
      content: (
        <div className="space-y-6">
          <Card padding="lg">
            <h3 className="text-lg font-semibold text-slate-100 mb-4">
              Executive Summary
            </h3>
            <p className="text-slate-300 leading-relaxed">
              {currentReport.executiveSummary}
            </p>
          </Card>

          <div>
            <h3 className="text-lg font-semibold text-slate-100 mb-4 flex items-center gap-2">
              <Lightbulb className="w-5 h-5 text-amber-400" />
              Key Recommendations
            </h3>
            <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
              {currentReport.keyRecommendations.map((recommendation, index) => (
                <Card key={index} padding="md" className="border-l-4 border-l-accent">
                  <div className="flex items-start gap-3">
                    <span className="flex-shrink-0 w-6 h-6 rounded-full bg-accent/20 text-accent flex items-center justify-center text-sm font-bold">
                      {index + 1}
                    </span>
                    <p className="text-slate-300">{recommendation}</p>
                  </div>
                </Card>
              ))}
            </div>
          </div>
        </div>
      ),
    },
    {
      id: 'risks',
      label: 'Risk Register',
      content: (
        <Card>
          <RiskRegisterTable risks={currentReport.riskRegister} />
        </Card>
      ),
    },
    {
      id: 'scenarios',
      label: 'Scenario Matrix',
      content: <ScenarioMatrixGrid scenarios={currentReport.scenarioMatrix} />,
    },
    {
      id: 'stakeholders',
      label: 'Stakeholder Heatmap',
      content: <StakeholderHeatmap stakeholders={currentReport.stakeholderHeatmap} />,
    },
    {
      id: 'full',
      label: 'Full Report',
      content: (
        <Card padding="lg">
          <div className="prose prose-invert max-w-none">
            <h2 className="text-2xl font-bold text-slate-100 mb-4">
              Complete Simulation Report
            </h2>
            <div className="space-y-6 text-slate-300">
              <section>
                <h3 className="text-xl font-semibold text-slate-200 mb-3">
                  Executive Summary
                </h3>
                <p>{currentReport.executiveSummary}</p>
              </section>
              
              <section>
                <h3 className="text-xl font-semibold text-slate-200 mb-3">
                  Methodology
                </h3>
                <p>
                  This simulation employed AI-driven agent modeling to explore strategic
                  scenarios and stakeholder dynamics. The analysis incorporated multiple
                  rounds of interaction between autonomous agents representing key
                  organizational roles.
                </p>
              </section>

              <section>
                <h3 className="text-xl font-semibold text-slate-200 mb-3">
                  Key Findings
                </h3>
                <ul className="list-disc list-inside space-y-2">
                  {currentReport.keyRecommendations.map((rec, idx) => (
                    <li key={idx}>{rec}</li>
                  ))}
                </ul>
              </section>

              <section>
                <h3 className="text-xl font-semibold text-slate-200 mb-3">
                  Risk Analysis
                </h3>
                <p>
                  The simulation identified {currentReport.riskRegister.length} key risks
                  across multiple categories including human capital, operational, and
                  strategic dimensions.
                </p>
              </section>

              <section>
                <h3 className="text-xl font-semibold text-slate-200 mb-3">
                  Recommendations
                </h3>
                <p>
                  Based on the simulation outcomes, we recommend immediate action on
                  high-priority items while monitoring medium-term risks through
                  established governance mechanisms.
                </p>
              </section>
            </div>
          </div>
        </Card>
      ),
    },
  ];

  return (
    <div className="space-y-4 md:space-y-6 animate-fade-in">
      {/* Header */}
      <div className="flex flex-col lg:flex-row lg:items-center justify-between gap-4">
        <div className="flex flex-col sm:flex-row sm:items-center gap-3 sm:gap-4">
          <Link href={`/simulations/${simulationId}`}>
            <Button variant="ghost" size="sm" leftIcon={<ChevronLeft className="w-4 h-4" />}>
              Back to Simulation
            </Button>
          </Link>
          <div className="min-w-0">
            <h1 className="text-2xl sm:text-3xl font-bold text-slate-100">
              Simulation Report
            </h1>
            <p className="text-slate-400 mt-1 text-sm sm:text-base truncate">
              {currentReport.simulationName}
            </p>
          </div>
        </div>
        <ExportButtons onExport={handleExport} isLoading={isExporting} />
      </div>

      {/* Report Meta */}
      <div className="flex items-center gap-6 text-sm text-slate-400">
        <div>
          Generated: {new Date(currentReport.generatedAt).toLocaleString()}
        </div>
        <div>
          Report ID: <span className="font-mono">{currentReport.id}</span>
        </div>
      </div>

      {/* Tabs */}
      <Tabs tabs={tabs} defaultTab="summary" />
    </div>
  );
}
