'use client';

import { clsx } from 'clsx';
import { Check } from 'lucide-react';

interface Step {
  id: string;
  label: string;
  description?: string;
}

interface StepWizardProps {
  steps: Step[];
  currentStep: number;
  className?: string;
}

export function StepWizard({ steps, currentStep, className }: StepWizardProps) {
  return (
    <div className={clsx('w-full', className)}>
      <div className="flex items-center">
        {steps.map((step, index) => {
          const isCompleted = index < currentStep;
          const isCurrent = index === currentStep;
          const isLast = index === steps.length - 1;

          return (
            <div key={step.id} className={clsx('flex items-center', !isLast && 'flex-1')}>
              {/* Step Circle */}
              <div className="flex flex-col items-center">
                <div
                  className={clsx(
                    'w-10 h-10 rounded-full flex items-center justify-center font-semibold text-sm transition-colors',
                    isCompleted && 'bg-accent text-white',
                    isCurrent && 'bg-accent/20 text-accent border-2 border-accent',
                    !isCompleted && !isCurrent && 'bg-slate-700 text-slate-400 border-2 border-slate-600'
                  )}
                >
                  {isCompleted ? (
                    <Check className="w-5 h-5" />
                  ) : (
                    index + 1
                  )}
                </div>
                <span
                  className={clsx(
                    'mt-2 text-xs font-medium whitespace-nowrap',
                    isCompleted || isCurrent ? 'text-slate-200' : 'text-slate-500'
                  )}
                >
                  {step.label}
                </span>
              </div>

              {/* Connector Line */}
              {!isLast && (
                <div
                  className={clsx(
                    'h-0.5 flex-1 mx-4 transition-colors',
                    isCompleted ? 'bg-accent' : 'bg-slate-700'
                  )}
                />
              )}
            </div>
          );
        })}
      </div>
    </div>
  );
}
