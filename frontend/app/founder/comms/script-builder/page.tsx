'use client';

import { useState } from 'react';
import Link from 'next/link';
import { ArrowLeft, MessageSquare, RefreshCw, AlertTriangle, Send, Sparkles, Copy, CheckCircle } from 'lucide-react';
import { sendFounderCopilotCommand } from '@/services/api';

interface ScriptResult {
  script?: string;
  tone?: string;
  word_count?: number;
  generated_at?: string;
}

export default function ScriptBuilderPage() {
  const [prompt, setPrompt] = useState('');
  const [tone, setTone] = useState('professional');
  const [result, setResult] = useState<ScriptResult | null>(null);
  const [history, setHistory] = useState<ScriptResult[]>([]);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [copied, setCopied] = useState(false);

  const generateScript = async () => {
    if (!prompt.trim()) return;
    setLoading(true);
    setError(null);
    try {
      const res = await sendFounderCopilotCommand({
        command: `Generate a ${tone} communication script: ${prompt}`,
        context: { tone, type: 'script_builder' },
      });
      const script: ScriptResult = {
        script: res?.response ?? res?.script ?? res?.result ?? 'No script generated.',
        tone,
        word_count: (res?.response ?? res?.script ?? '').split(/\s+/).length,
        generated_at: new Date().toISOString(),
      };
      setResult(script);
      setHistory(prev => [script, ...prev].slice(0, 10));
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Script generation failed');
    } finally {
      setLoading(false);
    }
  };

  const copyScript = () => {
    if (result?.script) {
      navigator.clipboard.writeText(result.script);
      setCopied(true);
      setTimeout(() => setCopied(false), 2000);
    }
  };

  return (
    <div className="min-h-screen bg-gray-950 text-white p-6">
      <div className="max-w-7xl mx-auto space-y-8">
        <div>
          <Link href="/founder/comms" className="text-gray-400 hover:text-white flex items-center gap-1 text-sm mb-2"><ArrowLeft className="w-4 h-4" /> Communications</Link>
          <h1 className="text-3xl font-bold flex items-center gap-3"><MessageSquare className="w-8 h-8 text-cyan-400" /> Script Builder</h1>
          <p className="text-gray-400 mt-1">AI-powered communication script generation with tone control</p>
        </div>

        {error && <div className="bg-red-900/30 border border-red-700 rounded-lg p-4 flex items-center gap-3"><AlertTriangle className="w-5 h-5 text-red-400" /><span className="text-red-300">{error}</span></div>}

        {/* Input */}
        <div className="bg-gray-900 border border-gray-800 rounded-lg p-6">
          <h2 className="text-lg font-semibold mb-4 flex items-center gap-2"><Sparkles className="w-5 h-5 text-cyan-400" /> Generate Script</h2>
          <textarea
            placeholder="Describe the communication you need (e.g., 'Patient notification about billing statement', 'Crew reminder about training deadline')..."
            value={prompt}
            onChange={(e) => setPrompt(e.target.value)}
            rows={4}
            className="w-full bg-gray-800 border border-gray-700 rounded px-4 py-3 text-sm text-white placeholder-gray-500 resize-none"
          />
          <div className="mt-4 flex items-center gap-4">
            <select value={tone} onChange={(e) => setTone(e.target.value)}
              className="bg-gray-800 border border-gray-700 rounded px-3 py-2 text-sm text-white">
              <option value="professional">Professional</option>
              <option value="empathetic">Empathetic</option>
              <option value="urgent">Urgent</option>
              <option value="formal">Formal</option>
              <option value="friendly">Friendly</option>
            </select>
            <button onClick={generateScript} disabled={loading || !prompt.trim()}
              className="px-6 py-2 bg-cyan-600 hover:bg-cyan-500 disabled:opacity-50 rounded-lg flex items-center gap-2 text-sm font-semibold">
              {loading ? <RefreshCw className="w-4 h-4 animate-spin" /> : <Send className="w-4 h-4" />}
              {loading ? 'Generating...' : 'Generate'}
            </button>
          </div>
        </div>

        {/* Result */}
        {result && (
          <div className="bg-gray-900 border border-cyan-700 rounded-lg p-6">
            <div className="flex items-center justify-between mb-4">
              <h2 className="text-lg font-semibold flex items-center gap-2"><MessageSquare className="w-5 h-5 text-cyan-400" /> Generated Script</h2>
              <button onClick={copyScript} className="flex items-center gap-1 text-sm text-gray-400 hover:text-white">
                {copied ? <CheckCircle className="w-4 h-4 text-emerald-400" /> : <Copy className="w-4 h-4" />}
                {copied ? 'Copied!' : 'Copy'}
              </button>
            </div>
            <div className="bg-gray-800 rounded-lg p-4 text-sm text-gray-200 whitespace-pre-wrap">{result.script}</div>
            <div className="mt-3 flex gap-4 text-xs text-gray-500">
              <span>Tone: {result.tone}</span>
              <span>~{result.word_count} words</span>
              <span>{result.generated_at ? new Date(result.generated_at).toLocaleTimeString() : ''}</span>
            </div>
          </div>
        )}

        {/* History */}
        {history.length > 1 && (
          <div className="bg-gray-900 border border-gray-800 rounded-lg p-6">
            <h2 className="text-lg font-semibold mb-4">Recent Scripts</h2>
            <div className="space-y-3">
              {history.slice(1).map((h, i) => (
                <div key={i} className="bg-gray-800 rounded p-3 text-sm text-gray-300 truncate">
                  <span className="text-gray-500 mr-2">[{h.tone}]</span>
                  {h.script?.slice(0, 150)}...
                </div>
              ))}
            </div>
          </div>
        )}
      </div>
    </div>
  );
}
