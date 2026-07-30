'use client';

import { clsx } from 'clsx';
import { Check } from 'lucide-react';

interface Step {
  readonly id: string;
  readonly label: string;
  readonly description?: string;
}

interface StepWizardProps {
  steps: readonly Step[];
  currentStep: number;
  maxVisitedStep?: number;
  onStepClick?: (index: number) => void;
  className?: string;
}

export function StepWizard({
  steps,
  currentStep,
  maxVisitedStep = currentStep,
  onStepClick,
  className,
}: StepWizardProps) {
  return (
    <div className={clsx('w-full', className)}>
      <div className="flex items-center">
        {steps.map((step, index) => {
          const isCompleted = index < currentStep;
          const isCurrent = index === currentStep;
          const isLast = index === steps.length - 1;
          const isClickable =
            !!onStepClick && index <= maxVisitedStep && index !== currentStep;

          return (
            <div key={step.id} className={clsx('flex items-center', !isLast && 'flex-1')}>
              <div className="flex flex-col items-center">
                {isClickable ? (
                  <button
                    type="button"
                    onClick={() => onStepClick(index)}
                    aria-label={`Go to ${step.label}`}
                    aria-current={isCurrent ? 'step' : undefined}
                    className={clsx(
                      'w-10 h-10 rounded-full flex items-center justify-center font-semibold text-sm transition-colors focus:outline-none focus-visible:ring-2 focus-visible:ring-accent',
                      isCompleted && 'bg-accent text-white hover:bg-accent/90',
                      isCurrent &&
                        'bg-accent/20 text-accent border-2 border-accent cursor-default',
                      !isCompleted &&
                        !isCurrent &&
                        'bg-background-tertiary text-foreground-muted border-2 border-border hover:border-accent/50',
                    )}
                  >
                    {isCompleted ? <Check className="w-5 h-5" /> : index + 1}
                  </button>
                ) : (
                  <div
                    className={clsx(
                      'w-10 h-10 rounded-full flex items-center justify-center font-semibold text-sm transition-colors',
                      isCompleted && 'bg-accent text-white',
                      isCurrent && 'bg-accent/20 text-accent border-2 border-accent',
                      !isCompleted &&
                        !isCurrent &&
                        'bg-background-tertiary text-foreground-muted border-2 border-border',
                    )}
                    aria-current={isCurrent ? 'step' : undefined}
                  >
                    {isCompleted ? <Check className="w-5 h-5" /> : index + 1}
                  </div>
                )}
                <span
                  className={clsx(
                    'mt-2 text-xs font-medium whitespace-nowrap',
                    isCompleted || isCurrent ? 'text-foreground' : 'text-foreground-subtle',
                  )}
                >
                  {step.label}
                </span>
              </div>

              {!isLast && (
                <div
                  className={clsx(
                    'h-0.5 flex-1 mx-4 transition-colors',
                    isCompleted ? 'bg-accent' : 'bg-background-tertiary',
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
