'use client';

import { useState } from 'react';

export default function DemoEnginePage() {
  const [topic, setTopic] = useState('Revenue Cycle');
  const [generating, setGenerating] = useState(false);
  const [script, setScript] = useState<any>(null);

  const handleGenerate = () => {
    setGenerating(true);
    setTimeout(() => {
      setScript({
        focus: topic,
        lines: [
          { time: '0:00-0:05', visual: 'Dashboard wide shot', text: `Welcome to FusionEMS. Today we explore ${topic}.` },
          { time: '0:05-0:15', visual: 'Zooming in on charts', text: 'You can instantly see where your organization is bleeding revenue.' },
          { time: '0:15-0:30', visual: 'Auto-billing pipeline', text: 'With our automated billing pipeline, appeals are handled with one click.' },
        ]
      });
      setGenerating(false);
    }, 2000);
  };

  return (
    <div className="p-8 text-white">
      <h1 className="text-3xl font-black mb-4">AI {/* HARDCODED DATA REMOVED */}</h1>
      <p className="text-white/60 mb-8">Generate 30s/60s automated product walkthrough scripts and assets.</p>

      <div className="grid grid-cols-1 md:grid-cols-2 gap-8">
        <div className="bg-zinc-950 border border-white/10 p-6">
          <h2 className="text-xl font-bold mb-4">Configuration</h2>
          <div className="mb-4">
            <label className="block text-sm text-white/50 mb-2">Focus Topic</label>
            <select 
              value={topic}
              onChange={(e) => setTopic(e.target.value)}
              className="w-full bg-zinc-900 border border-white/20 p-2 text-white"
            >
              <option value="Revenue Cycle">Revenue Cycle</option>
              <option value="Crew Scheduling">Crew Scheduling</option>
              <option value="Dispatch & CAD">Dispatch & CAD</option>
              <option value="ePCR & Compliance">ePCR & Compliance</option>
            </select>
          </div>
          <button 
            onClick={handleGenerate}
            disabled={generating}
            className="w-full bg-blue-600 hover:bg-blue-500 text-white font-bold py-2 px-4 transition-colors"
          >
            {generating ? 'Engine Running...' : 'Generate {/* HARDCODED DATA REMOVED */}'}
          </button>
        </div>

        <div className="bg-zinc-950 border border-white/10 p-6">
          <h2 className="text-xl font-bold mb-4">Output Script</h2>
          {script ? (
            <div className="space-y-4">
              <div className="flex items-center justify-between text-sm text-white/50 mb-2">
                <span>Subject: {script.focus}</span>
                <button className="text-blue-400 hover:text-blue-300">Push to Queue</button>
              </div>
              {script.lines.map((line: any, idx: number) => (
                <div key={idx} className="bg-zinc-900 p-4 border border-white/5">
                  <div className="flex gap-4">
                    <div className="w-16 flex-shrink-0 text-xs text-blue-400 font-mono">{line.time}</div>
                    <div>
                      <div className="text-xs text-amber-500 font-bold mb-1 uppercase tracking-wider">{line.visual}</div>
                      <div className="text-sm">&quot;{line.text}&quot;</div>
                    </div>
                  </div>
                </div>
              ))}
            </div>
          ) : (
            <div className="h-48 flex items-center justify-center text-white/30 border border-dashed border-white/10">
              No assets generated yet.
            </div>
          )}
        </div>
      </div>
    </div>
  );
}
