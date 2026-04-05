import { useState, useRef, useEffect, useId } from 'react';
import { ChevronDown } from 'lucide-react';
import { clsx } from 'clsx';

interface SelectOption {
  value: string;
  label: string;
}

interface SelectProps {
  label?: string;
  options: SelectOption[];
  value: string;
  onChange: (value: string) => void;
  className?: string;
}

export function Select({ label, options, value, onChange, className }: SelectProps) {
  const [isOpen, setIsOpen] = useState(false);
  const containerRef = useRef<HTMLDivElement>(null);
  const listboxRef = useRef<HTMLUListElement>(null);
  const buttonRef = useRef<HTMLButtonElement>(null);
  const id = useId();
  const labelId = `${id}-label`;
  const [focusedIndex, setFocusedIndex] = useState(-1);

  useEffect(() => {
    const handleClickOutside = (event: MouseEvent) => {
      if (containerRef.current && !containerRef.current.contains(event.target as Node)) {
        setIsOpen(false);
      }
    };
    document.addEventListener('mousedown', handleClickOutside);
    return () => document.removeEventListener('mousedown', handleClickOutside);
  }, []);

  useEffect(() => {
    if (isOpen) {
      if (listboxRef.current) {
        listboxRef.current.focus();
      }
    }
  }, [isOpen]);

  const handleKeyDown = (e: React.KeyboardEvent) => {
    switch (e.key) {
      case 'ArrowDown':
        e.preventDefault();
        if (options.length === 0) {
          setFocusedIndex(-1);
          break;
        }
        setFocusedIndex((prev) => (prev + 1) % options.length);
        break;
      case 'ArrowUp':
        e.preventDefault();
        if (options.length === 0) {
          setFocusedIndex(-1);
          break;
        }
        setFocusedIndex((prev) => (prev - 1 < 0 ? options.length - 1 : prev - 1));
        break;
      case 'Enter':
      case ' ':
        e.preventDefault();
        if (focusedIndex >= 0 && focusedIndex < options.length) {
          onChange(options[focusedIndex].value);
          buttonRef.current?.focus();
          setIsOpen(false);
        }
        break;
      case 'Escape':
        e.preventDefault();
        buttonRef.current?.focus();
        setIsOpen(false);
        break;
    }
  };

  const selectedOption = options.find((opt) => opt.value === value);

  return (
    <div className={clsx('relative', className)} ref={containerRef}>
      {label && (
        <label id={labelId} className="block text-sm font-medium text-foreground-muted mb-2">
          {label}
        </label>
      )}
      <button
        ref={buttonRef}
        type="button"
        aria-haspopup="listbox"
        aria-expanded={isOpen}
        aria-labelledby={label ? labelId : undefined}
        aria-label={label ? undefined : (selectedOption?.label ?? 'Select')}
        onClick={() => {
          if (!isOpen) {
            const idx = options.findIndex((opt) => opt.value === value);
            setFocusedIndex(idx >= 0 ? idx : 0);
          }
          setIsOpen(!isOpen);
        }}
        className="w-full flex items-center justify-between px-3 py-2 bg-background-tertiary border border-border rounded-lg text-foreground focus:outline-none focus:ring-2 focus:ring-accent"
      >
        <span className="truncate">{selectedOption?.label || 'Select...'}</span>
        <ChevronDown className="w-4 h-4 text-foreground-muted" />
      </button>

      {isOpen && (
        <ul
          ref={listboxRef}
          role="listbox"
          tabIndex={-1}
          aria-labelledby={label ? labelId : undefined}
          aria-activedescendant={focusedIndex >= 0 ? `${id}-option-${focusedIndex}` : undefined}
          onKeyDown={handleKeyDown}
          className="absolute z-10 mt-1 w-full bg-background-tertiary border border-border rounded-lg shadow-lg max-h-60 overflow-auto focus:outline-none"
        >
          {options.map((option, index) => (
            <li
              id={`${id}-option-${index}`}
              key={option.value}
              role="option"
              aria-selected={option.value === value}
              className={clsx(
                'cursor-pointer select-none px-3 py-2 text-sm',
                option.value === value
                  ? 'bg-accent/10 text-accent'
                  : focusedIndex === index
                  ? 'bg-background-secondary text-foreground'
                  : 'text-foreground hover:bg-background-secondary'
              )}
              onClick={() => {
                onChange(option.value);
                buttonRef.current?.focus();
                setIsOpen(false);
              }}
              onMouseEnter={() => setFocusedIndex(index)}
            >
              {option.label}
            </li>
          ))}
        </ul>
      )}
    </div>
  );
}
