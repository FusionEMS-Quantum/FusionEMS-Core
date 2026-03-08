import { describe, it, expect, vi } from 'vitest';
import { fireEvent, render, screen } from '@testing-library/react';

import {
  AIExplanationCard,
  SimpleModeSummary,
} from '@/components/ui/AIAssistant';
import { ReviewRequiredBanner } from '@/components/ui/ReviewRequiredBanner';
import { HumanOverrideBanner } from '@/components/ui/HumanOverrideBanner';

describe('AI assistant shared UI components', () => {
  it('renders AIExplanationCard with What/Why/Next content', () => {
    render(
      <AIExplanationCard
        what="Claim denied by payer"
        why="Revenue is blocked until appeal"
        next="Submit appeal packet"
        domain="billing"
        severity="HIGH"
      />
    );

    expect(screen.getByText('AI Insight')).toBeInTheDocument();
    expect(screen.getByText('Claim denied by payer')).toBeInTheDocument();
    expect(screen.getByText('Revenue is blocked until appeal')).toBeInTheDocument();
    expect(screen.getByText('→ Submit appeal packet')).toBeInTheDocument();
  });

  it('supports collapse/expand behavior', () => {
    render(
      <AIExplanationCard
        what="Queue pressure rising"
        why="Dispatch latency can increase"
        next="Drain queue workers"
      />
    );

    const collapseButton = screen.getByLabelText('Collapse');
    fireEvent.click(collapseButton);
    expect(screen.queryByText('What happened')).not.toBeInTheDocument();

    const expandButton = screen.getByLabelText('Expand');
    fireEvent.click(expandButton);
    expect(screen.getByText('What happened')).toBeInTheDocument();
  });

  it('invokes dismiss callback when dismiss button is clicked', () => {
    const onDismiss = vi.fn();

    render(
      <AIExplanationCard
        what="Telemetry outlier"
        why="Can hide production degradation"
        next="Inspect traces"
        onDismiss={onDismiss}
      />
    );

    fireEvent.click(screen.getByLabelText('Dismiss'));
    expect(onDismiss).toHaveBeenCalledTimes(1);
  });

  it('shows human review warning when requiresReview=true', () => {
    render(
      <AIExplanationCard
        what="Potential write-off"
        why="Could impact collections outcome"
        next="Escalate to billing supervisor"
        requiresReview
      />
    );

    expect(
      screen.getByText('Human review required before acting on this recommendation.')
    ).toBeInTheDocument();
  });

  it('renders SimpleModeSummary and optional warning block', () => {
    render(
      <SimpleModeSummary
        screenName="ePCR QA"
        whatThisDoes="Checks chart quality"
        whatIsWrong="Missing required assessment"
        whatMatters="Cannot submit locked chart"
        whatToClickNext="Open chart validation"
        requiresReview
      />
    );

    expect(screen.getByText('ePCR QA')).toBeInTheDocument();
    expect(screen.getByText('What is wrong here')).toBeInTheDocument();
    expect(screen.getByText('A human must review this before you proceed.')).toBeInTheDocument();
  });

  it('renders ReviewRequiredBanner and calls onReview', () => {
    const onReview = vi.fn();

    render(
      <ReviewRequiredBanner
        reason="AI recommends changing deployment rollback policy"
        onReview={onReview}
        reviewLabel="Review Change"
      />
    );

    expect(screen.getByText('Human Review Required')).toBeInTheDocument();
    fireEvent.click(screen.getByRole('button', { name: 'Review Change' }));
    expect(onReview).toHaveBeenCalledTimes(1);
  });

  it('renders HumanOverrideBanner details and audit callback', () => {
    const onViewAudit = vi.fn();

    render(
      <HumanOverrideBanner
        overriddenBy="Chief Billing Officer"
        timestamp="2026-03-07T10:15:00Z"
        reason="Payer policy exception confirmed"
        originalDecision="Deny appeal"
        onViewAudit={onViewAudit}
      />
    );

    expect(screen.getByText('Human Override Applied')).toBeInTheDocument();
    expect(screen.getByText(/Chief Billing Officer/)).toBeInTheDocument();
    expect(screen.getByText(/Original decision:/)).toBeInTheDocument();
    fireEvent.click(screen.getByRole('button', { name: 'View Audit →' }));
    expect(onViewAudit).toHaveBeenCalledTimes(1);
  });
});
