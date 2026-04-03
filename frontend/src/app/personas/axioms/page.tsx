'use client';

import { useState } from 'react';
import Link from 'next/link';
import { ChevronLeft, Upload, Brain, CheckCircle, AlertTriangle, FileText, Sparkles } from 'lucide-react';
import { Card } from '@/components/ui/Card';
import { Button } from '@/components/ui/Button';
import { api } from '@/lib/api';

interface ExtractedAxiom {
  id: string;
  statement: string;
  confidence: number;
  source: string;
  category: string;
}

interface ValidationResult {
  axiom_id: string;
  validated: boolean;
  holdout_accuracy: number;
  conflicts: string[];
}

// Mock data
const mockAxioms: ExtractedAxiom[] = [
  {
    id: 'axiom-1',
    statement: 'Always prioritize shareholder value in strategic decisions',
    confidence: 0.92,
    source: 'Board minutes Q4 2023',
    category: 'decision_making',
  },
  {
    id: 'axiom-2',
    statement: 'Risk tolerance decreases when market volatility exceeds 20%',
    confidence: 0.87,
    source: 'Earnings call Q3 2023',
    category: 'risk_assessment',
  },
  {
    id: 'axiom-3',
    statement: 'Prefer consensus-building over unilateral decisions',
    confidence: 0.78,
    source: 'War game outputs 2023',
    category: 'collaboration',
  },
  {
    id: 'axiom-4',
    statement: 'Data-driven arguments carry more weight than intuition',
    confidence: 0.85,
    source: 'Board minutes Q1 2024',
    category: 'communication',
  },
];

const mockValidations: ValidationResult[] = [
  {
    axiom_id: 'axiom-1',
    validated: true,
    holdout_accuracy: 0.89,
    conflicts: [],
  },
  {
    axiom_id: 'axiom-2',
    validated: true,
    holdout_accuracy: 0.82,
    conflicts: [],
  },
  {
    axiom_id: 'axiom-3',
    validated: false,
    holdout_accuracy: 0.64,
    conflicts: ['Contradicts observed behavior in crisis scenarios'],
  },
];

const dataTypes = [
  { value: 'board_minutes', label: 'Board Minutes', icon: FileText },
  { value: 'earnings_calls', label: 'Earnings Calls', icon: FileText },
  { value: 'war_game_outputs', label: 'War Game Outputs', icon: Brain },
];

export default function BehavioralAxiomsPage() {
  const [historicalData, setHistoricalData] = useState('');
  const [dataType, setDataType] = useState('board_minutes');
  const [isExtracting, setIsExtracting] = useState(false);
  const [isValidating, setIsValidating] = useState(false);
  const [axioms, setAxioms] = useState<ExtractedAxiom[]>([]);
  const [validations, setValidations] = useState<ValidationResult[]>([]);
  const [showValidation, setShowValidation] = useState(false);

  const handleExtract = async () => {
    setIsExtracting(true);
    try {
      // Mock API call
      await new Promise(resolve => setTimeout(resolve, 2000));
      setAxioms(mockAxioms);
      setShowValidation(false);
      setValidations([]);
    } catch {
      // Handle error
    }
    setIsExtracting(false);
  };

  const handleValidate = async () => {
    setIsValidating(true);
    try {
      // Mock API call
      await new Promise(resolve => setTimeout(resolve, 1500));
      setValidations(mockValidations);
      setShowValidation(true);
    } catch {
      // Handle error
    }
    setIsValidating(false);
  };

  const getAxiomValidation = (axiomId: string) => {
    return validations.find(v => v.axiom_id === axiomId);
  };

  return (
    <div className="space-y-6 animate-fade-in">
      {/* Header */}
      <div className="flex items-center gap-4">
        <Link href="/personas">
          <Button variant="ghost" size="sm" leftIcon={<ChevronLeft className="w-4 h-4" />}>
            Back
          </Button>
        </Link>
        <div>
          <h1 className="text-2xl sm:text-3xl font-bold text-slate-100">Behavioral Axioms Extractor</h1>
          <p className="text-slate-400 mt-1 text-sm sm:text-base">
            Extract behavioral patterns from historical data
          </p>
        </div>
      </div>

      <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
        {/* Input Section */}
        <div className="space-y-6">
          <Card
            header={
              <div className="flex items-center gap-2">
                <Upload className="w-5 h-5 text-accent" />
                <h2 className="text-lg font-semibold text-slate-100">Historical Data</h2>
              </div>
            }
          >
            <div className="space-y-4">
              <div>
                <label className="block text-sm font-medium text-slate-400 mb-2">
                  Data Type
                </label>
                <div className="grid grid-cols-3 gap-2">
                  {dataTypes.map((type) => (
                    <button
                      key={type.value}
                      onClick={() => setDataType(type.value)}
                      className={`flex flex-col items-center gap-2 p-3 rounded-lg border transition-colors ${
                        dataType === type.value
                          ? 'border-accent bg-accent/10 text-accent'
                          : 'border-slate-600 bg-slate-700/30 text-slate-400 hover:bg-slate-700/50'
                      }`}
                    >
                      <type.icon className="w-5 h-5" />
                      <span className="text-xs">{type.label}</span>
                    </button>
                  ))}
                </div>
              </div>

              <div>
                <label className="block text-sm font-medium text-slate-400 mb-2">
                  Historical Data Text
                </label>
                <textarea
                  value={historicalData}
                  onChange={(e) => setHistoricalData(e.target.value)}
                  className="w-full h-64 px-3 py-2 bg-slate-700/50 border border-slate-600 rounded-lg text-slate-200 focus:outline-none focus:border-accent resize-none"
                  placeholder={`Paste ${dataTypes.find(t => t.value === dataType)?.label.toLowerCase()} text here...`}
                />
              </div>

              <Button
                className="w-full"
                leftIcon={<Brain className="w-4 h-4" />}
                onClick={handleExtract}
                isLoading={isExtracting}
                disabled={!historicalData}
              >
                Extract Axioms
              </Button>
            </div>
          </Card>

          {/* Validation Section */}
          {axioms.length > 0 && (
            <Card
              header={
                <div className="flex items-center gap-2">
                  <CheckCircle className="w-5 h-5 text-accent" />
                  <h2 className="text-lg font-semibold text-slate-100">Validation</h2>
                </div>
              }
            >
              <div className="space-y-4">
                <p className="text-sm text-slate-400">
                  Validate extracted axioms against holdout data to ensure accuracy and identify conflicts.
                </p>
                <Button
                  className="w-full"
                  variant="secondary"
                  leftIcon={<Sparkles className="w-4 h-4" />}
                  onClick={handleValidate}
                  isLoading={isValidating}
                >
                  Validate Against Holdout Data
                </Button>
              </div>
            </Card>
          )}
        </div>

        {/* Output Section */}
        <div className="space-y-6">
          {axioms.length > 0 ? (
            <Card
              header={
                <div className="flex items-center gap-2">
                  <Brain className="w-5 h-5 text-accent" />
                  <h2 className="text-lg font-semibold text-slate-100">
                    Extracted Axioms ({axioms.length})
                  </h2>
                </div>
              }
            >
              <div className="space-y-4">
                {axioms.map((axiom) => {
                  const validation = getAxiomValidation(axiom.id);
                  return (
                    <div
                      key={axiom.id}
                      className={`p-4 rounded-lg border ${
                        validation
                          ? validation.validated
                            ? 'border-green-500/30 bg-green-500/5'
                            : 'border-red-500/30 bg-red-500/5'
                          : 'border-slate-600 bg-slate-700/20'
                      }`}
                    >
                      <div className="flex items-start justify-between gap-4">
                        <div className="flex-1">
                          <p className="text-slate-200 font-medium">{axiom.statement}</p>
                          <div className="flex items-center gap-3 mt-2 text-sm">
                            <span className="text-slate-500 capitalize">
                              {axiom.category.replace('_', ' ')}
                            </span>
                            <span className="text-slate-600">•</span>
                            <span className="text-slate-500">{axiom.source}</span>
                          </div>
                        </div>
                        <div className="text-right">
                          <div className={`text-sm font-medium ${
                            axiom.confidence >= 0.8 ? 'text-green-400' :
                            axiom.confidence >= 0.6 ? 'text-yellow-400' :
                            'text-red-400'
                          }`}>
                            {(axiom.confidence * 100).toFixed(0)}%
                          </div>
                          <div className="text-xs text-slate-500">confidence</div>
                        </div>
                      </div>

                      {validation && (
                        <div className="mt-3 pt-3 border-t border-slate-600/30">
                          <div className="flex items-center gap-2">
                            {validation.validated ? (
                              <>
                                <CheckCircle className="w-4 h-4 text-green-400" />
                                <span className="text-sm text-green-400">
                                  Validated ({(validation.holdout_accuracy * 100).toFixed(0)}% accuracy)
                                </span>
                              </>
                            ) : (
                              <>
                                <AlertTriangle className="w-4 h-4 text-red-400" />
                                <span className="text-sm text-red-400">
                                  Validation failed ({(validation.holdout_accuracy * 100).toFixed(0)}% accuracy)
                                </span>
                              </>
                            )}
                          </div>
                          {validation.conflicts.length > 0 && (
                            <ul className="mt-2 space-y-1">
                              {validation.conflicts.map((conflict, idx) => (
                                <li key={idx} className="text-sm text-red-400 flex items-start gap-2">
                                  <span>•</span>
                                  {conflict}
                                </li>
                              ))}
                            </ul>
                          )}
                        </div>
                      )}
                    </div>
                  );
                })}
              </div>
            </Card>
          ) : (
            <Card className="h-full flex items-center justify-center min-h-[400px]">
              <div className="text-center text-slate-500">
                <Brain className="w-12 h-12 mx-auto mb-4 opacity-50" />
                <p>Extract axioms to see results</p>
              </div>
            </Card>
          )}
        </div>
      </div>
    </div>
  );
}
