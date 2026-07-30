'use client';

import { useEffect, useRef } from 'react';

function resolveWsUrl(simulationId: string): string {
  const explicit = process.env.NEXT_PUBLIC_WS_URL?.replace(/\/$/, '');
  if (explicit) {
    return `${explicit}/api/simulations/ws/${simulationId}`;
  }
  const apiBase = process.env.NEXT_PUBLIC_API_URL?.replace(/\/$/, '');
  if (apiBase) {
    const wsBase = apiBase.replace(/^http/, 'ws');
    return `${wsBase}/api/simulations/ws/${simulationId}`;
  }
  if (typeof window !== 'undefined') {
    const proto = window.location.protocol === 'https:' ? 'wss' : 'ws';
    // Next rewrites HTTP /api only — WS talks directly to the backend port.
    return `${proto}://${window.location.hostname}:5001/api/simulations/ws/${simulationId}`;
  }
  return `ws://127.0.0.1:5001/api/simulations/ws/${simulationId}`;
}

export type SimulationSocketHandlers = {
  onMessage?: (payload: unknown) => void;
  onOpen?: () => void;
  onClose?: () => void;
  onError?: () => void;
};

/**
 * Connect to the simulation WebSocket while the monitor is live.
 * Falls back silently on connection failure — callers should keep HTTP polling.
 */
export function useSimulationSocket(
  simulationId: string,
  enabled: boolean,
  handlers: SimulationSocketHandlers
): void {
  const handlersRef = useRef(handlers);
  useEffect(() => {
    handlersRef.current = handlers;
  }, [handlers]);

  useEffect(() => {
    if (!enabled || !simulationId) return;

    let closed = false;
    let socket: WebSocket | null = null;
    let pingTimer: ReturnType<typeof setInterval> | null = null;
    let reconnectTimer: ReturnType<typeof setTimeout> | null = null;
    let attempt = 0;

    const clearTimers = () => {
      if (pingTimer) {
        clearInterval(pingTimer);
        pingTimer = null;
      }
      if (reconnectTimer) {
        clearTimeout(reconnectTimer);
        reconnectTimer = null;
      }
    };

    const connect = () => {
      if (closed) return;
      const url = resolveWsUrl(simulationId);
      try {
        socket = new WebSocket(url);
      } catch {
        handlersRef.current.onError?.();
        return;
      }

      socket.onopen = () => {
        attempt = 0;
        handlersRef.current.onOpen?.();
        pingTimer = setInterval(() => {
          if (socket?.readyState === WebSocket.OPEN) {
            socket.send(JSON.stringify({ action: 'ping' }));
          }
        }, 25_000);
      };

      socket.onmessage = (event) => {
        try {
          const data = JSON.parse(String(event.data)) as unknown;
          if (
            data &&
            typeof data === 'object' &&
            (data as { type?: string }).type === 'pong'
          ) {
            return;
          }
          handlersRef.current.onMessage?.(data);
        } catch {
          /* ignore non-JSON frames */
        }
      };

      socket.onerror = () => {
        handlersRef.current.onError?.();
      };

      socket.onclose = () => {
        clearTimers();
        handlersRef.current.onClose?.();
        if (closed) return;
        attempt += 1;
        const delay = Math.min(30_000, 1000 * 2 ** Math.min(attempt, 5));
        reconnectTimer = setTimeout(connect, delay);
      };
    };

    connect();

    return () => {
      closed = true;
      clearTimers();
      if (socket && socket.readyState <= WebSocket.OPEN) {
        socket.close();
      }
    };
  }, [simulationId, enabled]);
}
