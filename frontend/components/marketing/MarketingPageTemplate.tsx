import Link from 'next/link';
import { ArrowRight } from 'lucide-react';
import type { ReactNode } from 'react';

type AccentTone = 'orange' | 'blue' | 'green' | 'purple';

const ACCENT_STYLES: Record<AccentTone, { glow: string; border: string; text: string; chip: string }> = {
  orange: {
    glow: 'from-orange/15 via-orange/5 to-transparent',
    border: 'border-orange/35',
    text: 'text-[#FF4D00]',
    chip: 'bg-[#FF4D00]/12',
  },
  blue: {
    glow: 'from-system-fleet/20 via-system-fleet/5 to-transparent',
    border: 'border-system-fleet/35',
    text: 'text-system-fleet',
    chip: 'bg-system-fleet/12',
  },
  green: {
    glow: 'from-status-active/20 via-status-active/5 to-transparent',
    border: 'border-status-active/35',
    text: 'text-status-active',
    chip: 'bg-status-active/12',
  },
  purple: {
    glow: 'from-system-compliance/20 via-system-compliance/6 to-transparent',
    border: 'border-system-compliance/35',
    text: 'text-system-compliance',
    chip: 'bg-system-compliance/12',
  },
};

export interface MarketingStat {
  readonly label: string;
  readonly value: string;
  readonly detail?: string;
}

export interface MarketingFeature {
  readonly title: string;
  readonly description: string;
  readonly href?: string;
  readonly ctaLabel?: string;
}

export interface MarketingAction {
  readonly label: string;
  readonly href: string;
  readonly primary?: boolean;
}

interface MarketingPageTemplateProps {
  readonly eyebrow: string;
  readonly title: string;
  readonly description: string;
  readonly accent?: AccentTone;
  readonly signalLine?: string;
  readonly stats: readonly MarketingStat[];
  readonly features: readonly MarketingFeature[];
  readonly actions: readonly MarketingAction[];
  readonly children?: ReactNode;
}

export default function MarketingPageTemplate({
  eyebrow,
  title,
  description,
  accent = 'orange',
  signalLine,
  stats,
  features,
  actions,
  children,
}: MarketingPageTemplateProps) {
  const style = ACCENT_STYLES[accent];

  return (
    <section className="max-w-6xl mx-auto px-6 py-16 md:py-20 space-y-8 md:space-y-10">
      <div className="grid xl:grid-cols-[1.3fr_0.7fr] gap-4">
        <div className={`relative overflow-hidden border border-border-default chamfer-12 p-6 md:p-8 bg-[rgba(10,10,11,0.7)]`}>
          <div className={`absolute inset-0 bg-gradient-to-br ${style.glow} pointer-events-none`} />
          <div className="relative">
            <div className={`inline-flex items-center gap-2 px-3 py-1 chamfer-8 border ${style.border} ${style.chip}`}>
              <span className={`text-micro uppercase tracking-[0.16em] font-semibold ${style.text}`}>{eyebrow}</span>
            </div>

            <h1 className="text-display font-black mt-4 text-zinc-100 leading-tight">{title}</h1>
            <p className="text-body-lg text-zinc-400 mt-3 max-w-4xl">{description}</p>

            {signalLine && (
              <p className="text-micro uppercase tracking-[0.16em] text-zinc-500 mt-5">{signalLine}</p>
            )}

            <div className="flex flex-wrap gap-3 mt-6">
              {actions.map((action) => (
                <Link
                  key={action.href + action.label}
                  href={action.href}
                  className={action.primary ? 'quantum-btn-primary' : 'quantum-btn'}
                >
                  {action.label}
                  <ArrowRight className="w-3.5 h-3.5" />
                </Link>
              ))}
            </div>
          </div>
        </div>

        <div className="bg-[#0A0A0B] border border-border-default chamfer-12 p-6 flex flex-col justify-between">
          <div>
            <div className="text-micro uppercase tracking-[0.16em] text-zinc-500">Operational Signal</div>
            <div className={`text-h3 font-bold mt-2 ${style.text}`}>Deployment-ready public surface</div>
            <p className="text-body text-zinc-400 mt-3">
              Shared navigation, explicit conversion lanes, and role-separated access patterns are applied consistently across the public site.
            </p>
          </div>

          <div className="grid gap-3 mt-6">
            {stats.slice(0, 2).map((stat) => (
              <div key={stat.label} className="border border-border-default bg-[rgba(255,255,255,0.02)] chamfer-8 p-4">
                <div className="text-micro uppercase tracking-[0.14em] text-zinc-500">{stat.label}</div>
                <div className="text-h2 font-bold mt-1 text-zinc-100">{stat.value}</div>
                {stat.detail && <div className="text-body text-zinc-500 mt-1">{stat.detail}</div>}
              </div>
            ))}
          </div>
        </div>
      </div>

      <div className="grid md:grid-cols-2 xl:grid-cols-4 gap-3">
        {stats.map((stat) => (
          <div key={stat.label} className="bg-[#0A0A0B] border border-border-default chamfer-8 p-4">
            <div className="text-micro uppercase tracking-[0.14em] text-zinc-500">{stat.label}</div>
            <div className="text-h2 font-bold mt-1.5 text-zinc-100">{stat.value}</div>
            {stat.detail && <div className="text-body text-zinc-500 mt-1">{stat.detail}</div>}
          </div>
        ))}
      </div>

      <div className="grid md:grid-cols-2 gap-4">
        {features.map((feature) => {
          const content = (
            <>
              <div className="text-label uppercase tracking-widest text-zinc-500">Capability</div>
              <h2 className="text-h3 font-bold mt-1.5 text-zinc-100">{feature.title}</h2>
              <p className="text-body text-zinc-400 mt-2 leading-relaxed">{feature.description}</p>
              {feature.href && (
                <div className="mt-4 inline-flex items-center gap-1.5 text-label uppercase tracking-widest text-brand-orange-bright">
                  {feature.ctaLabel ?? 'Open'}
                  <ArrowRight className="w-3.5 h-3.5" />
                </div>
              )}
            </>
          );

          return feature.href ? (
            <Link key={feature.title} href={feature.href} className="bg-[#0A0A0B] border border-border-default hover:border-brand-orange/60 transition-colors chamfer-8 p-5">
              {content}
            </Link>
          ) : (
            <div key={feature.title} className="bg-[#0A0A0B] border border-border-default chamfer-8 p-5">
              {content}
            </div>
          );
        })}
      </div>

      {children}
    </section>
  );
}