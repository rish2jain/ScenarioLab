import { beforeEach, describe, expect, it } from 'vitest';
import { useChatStore } from './store';

describe('useChatStore.resetForSimulation', () => {
  beforeEach(() => {
    useChatStore.setState({
      messages: [
        {
          id: 'm1',
          simulationId: 'sim-old',
          content: 'hello',
          timestamp: new Date().toISOString(),
          isUser: true,
        },
      ],
      selectedAgentId: 'agent-stale',
      error: 'previous error',
      isLoading: false,
    });
  });

  it('clears messages, selected agent, and error', () => {
    useChatStore.getState().resetForSimulation();
    const state = useChatStore.getState();
    expect(state.messages).toEqual([]);
    expect(state.selectedAgentId).toBeNull();
    expect(state.error).toBeNull();
  });
});
