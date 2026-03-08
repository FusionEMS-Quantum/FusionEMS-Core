'use client';
import Link from 'next/link';

export default function CertificationPage() {
  return (
    <div className="p-5 min-h-screen">
      <div className="hud-rail pb-3 mb-6">
        <div className="micro-caps mb-1">Compliance Operations</div>
        <h1 className="text-h2 font-bold text-zinc-100">System Certification & AI Audits</h1>
        <p className="text-body text-zinc-500 mt-1">Unified Command Center for State and Federal Compliance Standards.</p>
      </div>
      
      <div className="grid grid-cols-1 md:grid-cols-2 gap-6">
        
        {/* NEMSIS Card */}
        <div className="bg-[#0A0A0B] border border-border-DEFAULT chamfer-8 p-6 shadow-elevation-1">
          <div className="flex justify-between items-start mb-4">
            <div>
              <div className="micro-caps text-green-500 mb-1">EMS Subsystem</div>
              <h2 className="text-h3 font-bold text-zinc-100">NEMSIS v3.5.1</h2>
            </div>
            <span className="px-2 py-1 text-micro font-mono uppercase bg-green-500/20 text-green-400 border border-green-500/30 chamfer-2">
              Ready
            </span>
          </div>
          <p className="text-sm text-zinc-500 mb-6 h-10">Federal EMS dispatch and ePCR data standard. 100% CI pass rate with active AI copilot.</p>
          <ul className="space-y-3 text-sm mb-6 text-zinc-100">
            <li className="flex items-center gap-2"><svg className="text-green-500 w-4 h-4" fill="none" viewBox="0 0 24 24" stroke="currentColor"><path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M5 13l4 4L19 7"/></svg> XSD Validation Strict</li>
            <li className="flex items-center gap-2"><svg className="text-green-500 w-4 h-4" fill="none" viewBox="0 0 24 24" stroke="currentColor"><path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M5 13l4 4L19 7"/></svg> Schematron Rules Applied</li>
            <li className="flex items-center gap-2"><svg className="text-[#FF4D00] w-4 h-4" fill="none" viewBox="0 0 24 24" stroke="currentColor"><path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M13 10V3L4 14h7v7l9-11h-7z"/></svg> AI Mapping Assistant Active</li>
          </ul>
          <Link href="/founder/compliance/nemsis" className="btn-quantum-primary w-full justify-center">
            View NEMSIS Audit
          </Link>
        </div>

        {/* NERIS Card */}
        <div className="bg-[#0A0A0B] border border-border-DEFAULT chamfer-8 p-6 shadow-elevation-1">
          <div className="flex justify-between items-start mb-4">
            <div>
              <div className="micro-caps text-red-500 mb-1">Fire Subsystem</div>
              <h2 className="text-h3 font-bold text-zinc-100">NERIS (Modernized)</h2>
            </div>
            <span className="px-2 py-1 text-micro font-mono uppercase bg-green-500/20 text-green-400 border border-green-500/30 chamfer-2">
              Ready
            </span>
          </div>
          <p className="text-sm text-zinc-500 mb-6 h-10">National Fire Incident Reporting migration. Passing all state rules with active AI copilot.</p>
          <ul className="space-y-3 text-sm mb-6 text-zinc-100">
            <li className="flex items-center gap-2"><svg className="text-green-500 w-4 h-4" fill="none" viewBox="0 0 24 24" stroke="currentColor"><path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M5 13l4 4L19 7"/></svg> NERIS Compliant Data Mapping</li>
            <li className="flex items-center gap-2"><svg className="text-green-500 w-4 h-4" fill="none" viewBox="0 0 24 24" stroke="currentColor"><path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M5 13l4 4L19 7"/></svg> State-Specific Packages</li>
            <li className="flex items-center gap-2"><svg className="text-[#FF4D00] w-4 h-4" fill="none" viewBox="0 0 24 24" stroke="currentColor"><path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M13 10V3L4 14h7v7l9-11h-7z"/></svg> AI Compliance Explainer Active</li>
          </ul>
          <Link href="/founder/compliance/neris" className="btn-quantum-primary w-full justify-center">
            View NERIS Audit
          </Link>
        </div>

      </div>
    </div>
  );
}
