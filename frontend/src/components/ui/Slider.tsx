'use client';

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
  const percentage = ((value - min) / (max - min)) * 100;

  const handleChange = (e: React.ChangeEvent<HTMLInputElement>) => {
    onChange(Number(e.target.value));
  };

  return (
    <div className={clsx('w-full', className)}>
      {(label || showValue) && (
        <div className="flex items-center justify-between mb-2">
          {label && (
            <label className="text-sm font-medium text-slate-300">{label}</label>
          )}
          {showValue && (
            <span className="text-sm font-medium text-accent">
              {valueFormatter(value)}
            </span>
          )}
        </div>
      )}
      <div className="relative h-2 bg-slate-700 rounded-full">
        {/* Track Fill */}
        <div
          className="absolute h-full bg-accent rounded-full"
          style={{ width: `${percentage}%` }}
        />
        {/* Input */}
        <input
          type="range"
          min={min}
          max={max}
          step={step}
          value={value}
          onChange={handleChange}
          className={clsx(
            'absolute inset-0 w-full h-full opacity-0 cursor-pointer',
            'focus:outline-none'
          )}
        />
        {/* Thumb */}
        <div
          className="absolute top-1/2 -translate-y-1/2 w-4 h-4 bg-accent rounded-full shadow-lg pointer-events-none transition-transform"
          style={{ left: `calc(${percentage}% - 8px)` }}
        />
      </div>
      <div className="flex justify-between mt-1">
        <span className="text-xs text-slate-500">{valueFormatter(min)}</span>
        <span className="text-xs text-slate-500">{valueFormatter(max)}</span>
      </div>
    </div>
  );
}
