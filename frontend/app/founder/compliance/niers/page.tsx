'use client';

import { useEffect, useState } from 'react';
import { AlertTriangle, ArrowLeft, Flame, RefreshCw, FileOutput, CheckCircle } from 'lucide-react';
import Link from 'next/link';
import { listNERISExports, validateNERIS } from '@/services/api';

interface NERISExport {
  id?: string;
  status?: string;
  incident_ids?: string[];
  created_at?: string;
  record_count?: number;
  errors?: string[];
}

export default function NIERSManagerPage() {
  const [exports, setExports] = useState<NERISExport[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [validating, setValidating] = useState(false);
  const [validationResult, setValidationResult] = useState<Record<string, unknown> | null>(null);
  const [incidentId, setIncidentId] = useState('');

  const loadData = async () => {
    setLoading(true);
    setError(null);
    try {
      const res = await listNERISExports();
      const data = Array.isArray(res?.exports) ? res.exports : Array.isArray(res) ? res : [];
      setExports(data);
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Failed to load NERIS data');
    } finally {
      setLoading(false);
    }
  };

  const handleValidate = async () => {
    if (!incidentId.trim()) return;
    setValidating(true);
    setValidationResult(null);
    try {
      const res = await validateNERIS(incidentId.trim());
      setValidationResult(res);
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Validation failed');
    } finally {
      setValidating(false);
    }
  };

  useEffect(() => { loadData(); }, []);

  if (loading) {
    return (
      <div className="min-h-screen bg-gray-950 text-white flex items-center justify-center">
        <RefreshCw className="w-8 h-8 animate-spin text-emerald-400" />
      </div>
    );
  }

  return (
    <div className="min-h-screen bg-gray-950 text-white p-6">
      <div className="max-w-7xl mx-auto space-y-8">
        <div className="flex items-center justify-between">
          <div>
            <Link href="/founder/compliance" className="text-gray-400 hover:text-white flex items-center gap-1 text-sm mb-2">
              <ArrowLeft className="w-4 h-4" /> Back to Compliance
            </Link>
            <h1 className="text-3xl font-bold flex items-center gap-3">
              <Flame className="w-8 h-8 text-orange-400" />
              NERIS Compliance Manager
            </h1>
            <p className="text-gray-400 mt-1">Fire incident NERIS exports, validation, and state submission</p>
          </div>
          <button onClick={loadData} className="px-4 py-2 bg-gray-800 hover:bg-gray-700 rounded-lg flex items-center gap-2 text-sm">
            <RefreshCw className="w-4 h-4" /> Refresh
          </button>
        </div>

        {error && (
          <div className="bg-red-900/30 border border-red-700 rounded-lg p-4 flex items-center gap-3">
            <AlertTriangle className="w-5 h-5 text-red-400" />
            <span className="text-red-300">{error}</span>
          </div>
        )}

        {/* Validate Incident */}
        <div className="bg-gray-900 border border-gray-800 rounded-lg p-6">
          <h2 className="text-lg font-semibold mb-4 flex items-center gap-2">
            <CheckCircle className="w-5 h-5 text-emerald-400" /> Validate NERIS Mapping
          </h2>
          <div className="flex gap-3">
            <input
              type="text"
              value={incidentId}
              onChange={(e) => setIncidentId(e.target.value)}
              placeholder="Enter incident ID to validate..."
              className="flex-1 bg-gray-800 border border-gray-700 rounded-lg px-4 py-2 text-sm"
            />
            <button
              onClick={handleValidate}
              disabled={validating || !incidentId.trim()}
              className="px-4 py-2 bg-emerald-600 hover:bg-emerald-500 disabled:opacity-50 rounded-lg text-sm font-medium"
            >
              {validating ? 'Validating...' : 'Validate'}
            </button>
          </div>
          {validationResult && (
            <div className="mt-4 bg-gray-800 rounded-lg p-4">
              <pre className="text-sm text-gray-300 whitespace-pre-wrap">{JSON.stringify(validationResult, null, 2)}</pre>
            </div>
          )}
        </div>

        {/* Export History */}
        <div className="bg-gray-900 border border-gray-800 rounded-lg p-6">
          <h2 className="text-lg font-semibold mb-4 flex items-center gap-2">
            <FileOutput className="w-5 h-5 text-blue-400" /> NERIS Export History
          </h2>
          {exports.length > 0 ? (
            <div className="overflow-x-auto">
              <table className="w-full text-sm">
                <thead><tr className="text-gray-400 border-b border-gray-800">
                  <th className="text-left py-2">Export ID</th>
                  <th className="text-left py-2">Status</th>
                  <th className="text-right py-2">Records</th>
                  <th className="text-left py-2">Created</th>
                  <th className="text-left py-2">Errors</th>
                </tr></thead>
                <tbody>
                  {exports.map((e, i) => (
                    <tr key={i} className="border-b border-gray-800/50">
                      <td className="py-2 font-mono text-xs">{e.id ? e.id.slice(0, 8) + '...' : '—'}</td>
                      <td className={`py-2 ${e.status === 'completed' ? 'text-emerald-400' : e.status === 'failed' ? 'text-red-400' : 'text-amber-400'}`}>
                        {e.status ?? '—'}
                      </td>
                      <td className="py-2 text-right">{e.record_count ?? e.incident_ids?.length ?? (() => { throw new Error('Unsafe silent fallback. Dependency missing.'); })()}</td>
                      <td className="py-2 text-gray-400">{e.created_at ?? '—'}</td>
                      <td className="py-2 text-red-400 text-xs">{e.errors?.join(', ') || '—'}</td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          ) : (
            <div className="text-gray-500">No NERIS exports recorded. Exports will appear here once fire incidents are submitted.</div>
          )}
        </div>
      </div>
    </div>
  );
}
