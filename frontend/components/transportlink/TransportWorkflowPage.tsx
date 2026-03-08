import Link from 'next/link';

export interface WorkflowAction {
  readonly label: string;
  readonly href: string;
  readonly tone?: 'orange' | 'blue' | 'green' | 'purple';
}

interface TransportWorkflowPageProps {
  readonly backHref: string;
  readonly backLabel: string;
  readonly eyebrow: string;
  readonly title: string;
  readonly subtitle: string;
  readonly workflows: readonly string[];
  readonly actions: readonly WorkflowAction[];
}

const ACTION_STYLE: Record<NonNullable<WorkflowAction['tone']>, string> = {
  orange: 'bg-[#FF4D00]/15 border-orange/35 text-[#FF4D00] hover:bg-[#FF4D00]/25',
  blue: 'bg-system-fleet/15 border-system-fleet/35 text-system-fleet hover:bg-system-fleet/25',
  green: 'bg-status-active/15 border-status-active/35 text-status-active hover:bg-status-active/25',
  purple: 'bg-system-compliance/15 border-system-compliance/35 text-system-compliance hover:bg-system-compliance/25',
};

export default function TransportWorkflowPage({
  backHref,
  backLabel,
  eyebrow,
  title,
  subtitle,
  workflows,
  actions,
}: TransportWorkflowPageProps) {
  return (
    <div className="p-6 max-w-6xl mx-auto space-y-6">
      <div className="border border-border-default bg-[#0A0A0B]-raised/60 chamfer-12 p-6 relative overflow-hidden">
        <div className="absolute inset-0 pointer-events-none bg-gradient-to-br from-orange/15 via-orange/5 to-transparent" />
        <div className="relative">
          <Link href={backHref} className="text-body text-[#FF4D00]-400 hover:text-[#FF4D00]-300 mb-2 inline-block">
            ← {backLabel}
          </Link>
          <div className="text-micro uppercase tracking-[0.16em] text-brand-orange-bright">{eyebrow}</div>
          <h1 className="text-h1 font-black text-white mt-1">{title}</h1>
          <p className="text-body text-zinc-500 mt-2 max-w-3xl">{subtitle}</p>
        </div>
      </div>

      <div className="bg-zinc-950/[0.03] border border-white/[0.08] chamfer-8 p-4 space-y-3">
        <div className="text-micro uppercase tracking-widest text-zinc-500">Active Workflow Lanes</div>
        <div className="grid grid-cols-1 md:grid-cols-2 gap-3">
          {workflows.map((workflow) => (
            <div key={workflow} className="px-3 py-2 bg-zinc-950/[0.04] border border-white/[0.08] chamfer-8 text-sm text-white">
              {workflow}
            </div>
          ))}
        </div>
      </div>

      <div className="flex flex-wrap gap-2">
        {actions.map((action) => (
          <Link
            key={action.href + action.label}
            href={action.href}
            className={`px-4 py-2 border text-body font-bold chamfer-8 transition-colors ${ACTION_STYLE[action.tone ?? 'orange']}`}
          >
            {action.label}
          </Link>
        ))}
      </div>
    </div>
  );
}