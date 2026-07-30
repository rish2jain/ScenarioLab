'use client';

import { useId } from 'react';
import { clsx } from 'clsx';

interface SliderProps {
  label?: string;
  min: number;
  max: number;
  step?: number;
  value: number;
  onChange: (value: number) => void;
  showValue?: boolean;
  valueFormatter?: (value: number) => string;
  className?: string;
}

export function Slider({
  label,
  min,
  max,
  step = 1,
  value,
  onChange,
  showValue = true,
  valueFormatter = (v) => v.toString(),
  className,
}: SliderProps) {
  const inputId = useId();
  const percentage = ((value - min) / (max - min)) * 100;

  const handleChange = (e: React.ChangeEvent<HTMLInputElement>) => {
    onChange(Number(e.target.value));
  };

  return (
    <div className={clsx('w-full', className)}>
      {(label || showValue) && (
        <div className="flex items-center justify-between mb-2">
          {label && (
            <label htmlFor={inputId} className="text-sm font-medium text-foreground-muted">
              {label}
            </label>
          )}
          {showValue && (
            <span className="text-sm font-medium text-accent" aria-hidden="true">
              {valueFormatter(value)}
            </span>
          )}
        </div>
      )}
      <div className="relative h-2 bg-background-tertiary rounded-full">
        <div
          className="absolute h-full bg-accent rounded-full"
          style={{ width: `${percentage}%` }}
          aria-hidden="true"
        />
        <input
          id={inputId}
          type="range"
          min={min}
          max={max}
          step={step}
          value={value}
          onChange={handleChange}
          aria-valuenow={value}
          aria-valuemin={min}
          aria-valuemax={max}
          aria-label={label}
          className={clsx(
            'peer absolute inset-0 w-full h-full opacity-0 cursor-pointer',
            'focus:outline-none'
          )}
        />
        <div
          className={clsx(
            'absolute top-1/2 -translate-y-1/2 w-4 h-4 bg-accent rounded-full shadow-lg pointer-events-none transition-transform',
            'peer-focus-visible:ring-2 peer-focus-visible:ring-accent peer-focus-visible:ring-offset-2 peer-focus-visible:ring-offset-background'
          )}
          style={{ left: `calc(${percentage}% - 8px)` }}
          aria-hidden="true"
        />
      </div>
      <div className="flex justify-between mt-1" aria-hidden="true">
        <span className="text-xs text-foreground-subtle">{valueFormatter(min)}</span>
        <span className="text-xs text-foreground-subtle">{valueFormatter(max)}</span>
      </div>
    </div>
  );
}
