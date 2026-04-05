'use client';

import {
  Component,
  ReactNode,
  ErrorInfo,
  isValidElement,
  cloneElement,
  type ReactElement,
} from 'react';
import { Button } from './Button';
import { AlertCircle } from 'lucide-react';
import { reportCapturedError } from '@/lib/error-reporting';

/** Props injected when `fallback` is a component element or render function. */
export type ErrorBoundaryFallbackProps = {
  resetErrorBoundary: () => void;
  error?: Error | null;
};

interface ErrorBoundaryProps {
  children: ReactNode;
  fallback?:
    | ReactNode
    | ((props: ErrorBoundaryFallbackProps) => ReactNode);
  onReset?: () => void;
}

interface ErrorBoundaryState {
  hasError: boolean;
  error: Error | null;
}

export class ErrorBoundary extends Component<ErrorBoundaryProps, ErrorBoundaryState> {
  constructor(props: ErrorBoundaryProps) {
    super(props);
    this.state = { hasError: false, error: null };
  }

  static getDerivedStateFromError(error: Error): ErrorBoundaryState {
    return { hasError: true, error };
  }

  componentDidCatch(error: Error, errorInfo: ErrorInfo) {
    console.error('ErrorBoundary caught an error:', error, errorInfo);
    reportCapturedError(error, errorInfo);
  }

  resetErrorBoundary = () => {
    this.setState({ hasError: false, error: null });
    this.props.onReset?.();
  };

  render() {
    if (this.state.hasError) {
      const { fallback } = this.props;
      if (fallback !== undefined && fallback !== null) {
        if (typeof fallback === 'function') {
          return fallback({
            resetErrorBoundary: this.resetErrorBoundary,
            error: this.state.error,
          });
        }
        if (isValidElement(fallback)) {
          // Only custom (non-DOM) components accept arbitrary props; host elements
          // (e.g. div) must not receive resetErrorBoundary as an invalid attribute.
          if (typeof fallback.type === 'string') {
            return fallback;
          }
          return cloneElement(
            fallback as ReactElement<ErrorBoundaryFallbackProps>,
            {
              resetErrorBoundary: this.resetErrorBoundary,
              error: this.state.error,
            },
          );
        }
        return fallback;
      }

      return (
        <div className="flex flex-col items-center justify-center p-8 bg-background-secondary rounded-lg border border-border">
          <AlertCircle className="w-12 h-12 text-error mb-4" />
          <h2 className="text-xl font-semibold text-foreground mb-2">Something went wrong</h2>
          <p className="text-foreground-muted mb-6 text-center max-w-md">
            {process.env.NODE_ENV === 'development'
              ? (this.state.error?.message || 'An unexpected error occurred while rendering this component.')
              : 'An unexpected error occurred while rendering this component.'}
          </p>
          <Button onClick={this.resetErrorBoundary} variant="secondary">
            Try again
          </Button>
        </div>
      );
    }

    return this.props.children;
  }
}
