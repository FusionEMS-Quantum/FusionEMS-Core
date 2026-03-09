'use client';

import { useState } from 'react';

export default function VisualAutomationDesignerPage() {
  const [nodes] = useState([
    { id: 1, type: 'trigger', text: 'New Lead Captured (ROI Calculator)' },
    { id: 2, type: 'action', text: 'Score Lead' },
    { id: 3, type: 'condition', text: 'Score > 50?' },
    { id: 4, type: 'action', text: 'Send VIP Email Sequence' },
    { id: 5, type: 'action', text: 'Add to Nurture Drip' }
  ]);

  return (
    <div className="p-8 text-white h-[calc(100vh-4rem)] flex flex-col">
      <div className="mb-6">
        <h1 className="text-3xl font-black mb-2">Visual Automation Designer</h1>
        <p className="text-white/60">Drag and drop workflows for leads and marketing triggers.</p>
      </div>

      <div className="flex-1 bg-zinc-950 border border-white/10 relative overflow-hidden flex items-center justify-center">
        {/* Simplified conceptual visual board */}
        <div className="absolute top-4 left-4 bg-zinc-900 border border-white/20 p-2 flex flex-col gap-2">
          <div className="text-xs text-white/50 mb-1 font-bold uppercase tracking-wider">Blocks</div>
          <button className="bg-zinc-800 text-sm py-1.5 px-3 hover:bg-zinc-700 text-left border-l-2 border-blue-500">Trigger</button>
          <button className="bg-zinc-800 text-sm py-1.5 px-3 hover:bg-zinc-700 text-left border-l-2 border-emerald-500">Action</button>
          <button className="bg-zinc-800 text-sm py-1.5 px-3 hover:bg-zinc-700 text-left border-l-2 border-amber-500">Delay</button>
        </div>

        <div className="flex flex-col items-center gap-6">
          <div className="bg-blue-900/20 border border-blue-500/50 p-4 w-64 text-center rounded">
            <div className="text-xs text-blue-400 font-bold mb-1 uppercase">Trigger</div>
            {nodes[0].text}
          </div>
          
          <div className="w-px h-6 bg-white/20 block"></div>
          
          <div className="bg-emerald-900/20 border border-emerald-500/50 p-4 w-64 text-center rounded">
            <div className="text-xs text-emerald-400 font-bold mb-1 uppercase">Action</div>
            {nodes[1].text}
          </div>

          <div className="w-px h-6 bg-white/20 block"></div>

          <div className="bg-amber-900/20 border border-amber-500/50 p-4 w-64 text-center rounded transform origin-center rotate-45 scale-y-75">
            <div className="transform origin-center -rotate-45 scale-y-125">
              <div className="text-xs text-amber-500 font-bold mb-1 uppercase">Condition</div>
              {nodes[2].text}
            </div>
          </div>

          <div className="flex gap-16 mt-6">
            <div className="flex flex-col items-center gap-6">
              <div className="text-xs text-emerald-400 font-bold">YES</div>
              <div className="bg-emerald-900/20 border border-emerald-500/50 p-3 w-48 text-center rounded text-sm">
                {nodes[3].text}
              </div>
            </div>
            
            <div className="flex flex-col items-center gap-6">
              <div className="text-xs text-zinc-500 font-bold">NO</div>
              <div className="bg-emerald-900/20 border border-emerald-500/50 p-3 w-48 text-center rounded text-sm text-white/70">
                {nodes[4].text}
              </div>
            </div>
          </div>
        </div>
      </div>
    </div>
  );
}
