import { describe, it, expect, beforeEach, vi } from 'vitest';
import { render, screen, waitFor } from '@testing-library/react';

import PlatformCommandCenterPage from '@/app/founder/platform/page';
import {
  getPlatformHealth,
  getTechAssistantIssues,
  listPlatformIncidents,
} from '@/services/api';

vi.mock('@/services/api', () => ({
  getPlatformHealth: vi.fn(),
  listPlatformIncidents: vi.fn(),
  getTechAssistantIssues: vi.fn(),
}));

const getPlatformHealthMock = vi.mocked(getPlatformHealth);
const listPlatformIncidentsMock = vi.mocked(listPlatformIncidents);
const getTechAssistantIssuesMock = vi.mocked(getTechAssistantIssues);

describe('Founder Platform Command Center page', () => {
  beforeEach(() => {
    vi.clearAllMocks();
  });

  it('loads and renders platform telemetry and AI issue context', async () => {
    getPlatformHealthMock.mockResolvedValue({
      score: 88,
      status: 'YELLOW',
      timestamp: '2026-03-07T00:00:00Z',
      services: [{ name: 'api', status: 'GREEN', latency_ms: 42, uptime: '99.99%' }],
      integrations: [{ name: 'stripe', status: 'GREEN', last_sync: 'ok' }],
      queues: [{ name: 'billing_events', depth: 3, status: 'GREEN' }],
      ci_cd: { last_build: 'success', branch: 'main', deployment: 'healthy' },
    });

    listPlatformIncidentsMock.mockResolvedValue([
      {
        id: 'inc-1',
        title: 'Dispatch queue lag',
        severity: 'HIGH',
        state: 'OPEN',
        created_at: '2026-03-07T12:00:00Z',
      },
    ]);

    getTechAssistantIssuesMock.mockResolvedValue([
      {
        issue: 'Queue lag rising',
        severity: 'HIGH',
        source: 'ops',
        what_changed: 'Queue depth climbed over threshold.',
        why_it_matters: 'Delayed dispatch decisions can impact care windows.',
        what_you_should_do: 'Scale workers and inspect slow consumers.',
        executive_context: 'Revenue and SLA risk if sustained.',
        human_review: 'REQUIRED',
        confidence: 'HIGH',
      },
    ]);

    render(<PlatformCommandCenterPage />);

    expect(await screen.findByText('Platform Command Center')).toBeInTheDocument();
    expect(screen.getByText('88%')).toBeInTheDocument();
    expect(screen.getAllByText('Dispatch queue lag').length).toBeGreaterThan(0);
    expect(screen.getAllByText('Queue depth climbed over threshold.').length).toBeGreaterThan(0);
    expect(screen.getByText('Executive AI Analyst')).toBeInTheDocument();

    await waitFor(() => {
      expect(getPlatformHealthMock).toHaveBeenCalledTimes(1);
      expect(listPlatformIncidentsMock).toHaveBeenCalledWith(true);
      expect(getTechAssistantIssuesMock).toHaveBeenCalledTimes(1);
    });
  });

  it('shows hard-failure panel when health load fails', async () => {
    getPlatformHealthMock.mockRejectedValue(new Error('health endpoint unavailable'));
    listPlatformIncidentsMock.mockResolvedValue([]);
    getTechAssistantIssuesMock.mockResolvedValue([]);

    render(<PlatformCommandCenterPage />);

    expect(await screen.findByText('Platform command unavailable')).toBeInTheDocument();
    expect(screen.getByText('health endpoint unavailable')).toBeInTheDocument();
  });
});
