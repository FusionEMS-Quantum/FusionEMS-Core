// ── Core Components ───────────────────────────────────────────────
export { Button, buttonVariants } from './Button';
export type { ButtonProps } from './Button';

export { StatusChip, UnitStatusChip, ClaimStatusChip } from './StatusChip';
export type { StatusChipProps, UnitStatusChipProps, ClaimStatusChipProps } from './StatusChip';

export { PlateCard, MetricPlate } from './PlateCard';
export type { PlateCardProps, MetricPlateProps } from './PlateCard';

export { Input, Textarea } from './Input';
export type { InputProps, TextareaProps } from './Input';

export { QuantumTable } from './QuantumTable';
export type { QuantumTableProps, QuantumTableColumn } from './QuantumTable';

export { QuantumModal } from './QuantumModal';
export type { QuantumModalProps } from './QuantumModal';

export { QuantumEmptyState } from './QuantumEmptyState';
export type { QuantumEmptyStateProps } from './QuantumEmptyState';

export { ModuleUnavailable } from './ModuleUnavailable';
export type { ModuleUnavailableProps, DependencyStatus, DependencyInfo } from './ModuleUnavailable';

export { QuantumSkeleton, QuantumCardSkeleton, QuantumTableSkeleton } from './QuantumSkeleton';
export type { QuantumSkeletonProps } from './QuantumSkeleton';

export { QuantumHeader } from './QuantumHeader';
export type { QuantumHeaderProps } from './QuantumHeader';

export { QuantumCommandBar } from './QuantumCommandBar';
export type { QuantumCommandBarProps, CommandBarAction } from './QuantumCommandBar';

// ── Design System Components ─────────────────────────────────────
export { SeverityBadge } from './SeverityBadge';
export type { SeverityBadgeProps } from './SeverityBadge';

export { HealthScoreCard } from './HealthScoreCard';
export type { HealthScoreCardProps } from './HealthScoreCard';

export { MetricCard } from './MetricCard';
export type { MetricCardProps } from './MetricCard';

export { TimelinePanel } from './TimelinePanel';
export type { TimelinePanelProps, TimelineEvent } from './TimelinePanel';

export { NextBestActionCard } from './NextBestActionCard';
export type { NextBestActionCardProps, NextAction } from './NextBestActionCard';

export { AuditEventList } from './AuditEventList';
export type { AuditEventListProps, AuditEvent } from './AuditEventList';

export { ErrorState } from './ErrorState';
export type { ErrorStateProps } from './ErrorState';

export { ReviewRequiredBanner } from './ReviewRequiredBanner';
export type { ReviewRequiredBannerProps } from './ReviewRequiredBanner';

export { HumanOverrideBanner } from './HumanOverrideBanner';
export type { HumanOverrideBannerProps } from './HumanOverrideBanner';

// ── Interaction Patterns ─────────────────────────────────────────
export { FilterBar, TabBar, TabPanel, RecordSummary, SimpleModeToggle, DrilldownDrawer } from './InteractionPatterns';
export type {
  FilterBarProps,
  FilterOption,
  TabBarProps,
  TabItem,
  TabPanelProps,
  RecordSummaryProps,
  SimpleModeToggleProps,
  DrilldownDrawerProps,
} from './InteractionPatterns';

// ── Product Polish ───────────────────────────────────────────────
export {
  ConfirmDialog,
  ToastProvider,
  useToast,
  PartialDataWarning,
  DegradedModeWarning,
  RetryAffordance,
  SuccessConfirmation,
  LoadingOverlay,
} from './ProductPolish';
export type {
  ConfirmDialogProps,
  ToastVariant,
  Toast,
  PartialDataWarningProps,
  DegradedModeWarningProps,
  RetryAffordanceProps,
  SuccessConfirmationProps,
  LoadingOverlayProps,
} from './ProductPolish';

// ── AI Assistant ─────────────────────────────────────────────────
export { AIExplanationCard, AIContextPanel, SimpleModeSummary } from './AIAssistant';
export type {
  AIExplanationCardProps,
  AIContextPanelProps,
  SimpleModeSummaryProps,
} from './AIAssistant';

// ── Responsive Layer ─────────────────────────────────────────────
export {
  ViewportProvider,
  useViewport,
  Responsive,
  StickyActionSummary,
  DensitySelector,
  WidescreenSplit,
  TouchSafeButton,
} from './ResponsiveLayer';
export type {
  ResponsiveProps,
  StickyActionSummaryProps,
  DensitySelectorProps,
  WidescreenSplitProps,
  TouchSafeButtonProps,
} from './ResponsiveLayer';
