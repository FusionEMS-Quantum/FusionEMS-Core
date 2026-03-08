import Link from 'next/link';

const cards = [
  ['Founder Command', '/app/founder'],
  ['Billing Command', '/app/billing'],
  ['ePCR Command', '/app/epcr'],
  ['Operations Command', '/app/ops'],
  ['Scheduling Command', '/app/scheduling'],
  ['Fleet Command', '/app/fleet'],
  ['Compliance Command', '/app/compliance'],
  ['Communications Command', '/app/communications'],
  ['Analytics Command', '/app/analytics'],
  ['Platform Admin', '/app/admin'],
];

export default function AppHomePage() {
  return (
    <div className="space-y-5">
      <div>
        <div className="text-micro uppercase tracking-[0.16em] text-brand-orange-bright">App Home</div>
        <h1 className="text-h1 font-bold mt-1">Role-aware Command Routing</h1>
        <p className="text-body text-zinc-400 mt-1">Select the operational domain for your role.</p>
      </div>
      <div className="grid sm:grid-cols-2 lg:grid-cols-3 gap-3">
        {cards.map(([label, href]) => (
          <Link key={href} href={href} className="bg-[#0A0A0B] border border-border-default chamfer-8 p-4 hover:border-brand-orange transition-colors">
            <div className="text-label uppercase tracking-widest text-zinc-500">Module</div>
            <div className="text-h3 font-bold mt-2">{label}</div>
          </Link>
        ))}
      </div>
    </div>
  );
}
