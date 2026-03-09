'use client';

import { useEffect, useState } from 'react';
import Link from 'next/link';
import { ArrowLeft, ListTodo, RefreshCw, AlertTriangle, CheckCircle, Clock, CircleDot, Filter } from 'lucide-react';
import { getExpiringCredentials, getSchedulingCoverageDashboard } from '@/services/api';

interface TaskItem {
  id: string;
  title: string;
  category: string;
  priority: string;
  status: string;
  due_date?: string;
  assigned_to?: string;
}

export default function TaskCenterPage() {
  const [tasks, setTasks] = useState<TaskItem[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [filter, setFilter] = useState<string>('all');

  const loadData = async () => {
    setLoading(true);
    setError(null);
    try {
      const [credRes, covRes] = await Promise.allSettled([
        getExpiringCredentials(),
        getSchedulingCoverageDashboard(),
      ]);

      const derivedTasks: TaskItem[] = [];

      if (credRes.status === 'fulfilled') {
        const creds = Array.isArray(credRes.value?.credentials) ? credRes.value.credentials : Array.isArray(credRes.value) ? credRes.value : [];
        creds.forEach((c: { id: string; user_name?: string; credential_type?: string; expires_at?: string }) => {
          derivedTasks.push({
            id: `cred-${c.id}`,
            title: `Renew ${c.credential_type ?? 'credential'} for ${c.user_name ?? 'crew member'}`,
            category: 'Compliance',
            priority: 'high',
            status: 'pending',
            due_date: c.expires_at,
            assigned_to: c.user_name,
          });
        });
      }

      if (covRes.status === 'fulfilled' && covRes.value?.gap_count > 0) {
        derivedTasks.push({
          id: 'cov-gap',
          title: `Fill ${covRes.value.gap_count} coverage gap(s) in shift schedule`,
          category: 'Operations',
          priority: 'high',
          status: 'pending',
        });
      }

      setTasks(derivedTasks);
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Failed to load tasks');
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => { loadData(); }, []);

  const filteredTasks = filter === 'all' ? tasks : tasks.filter(t => t.category.toLowerCase() === filter);

  const priorityColor = (p: string) => {
    if (p === 'critical') return 'text-red-400';
    if (p === 'high') return 'text-amber-400';
    if (p === 'medium') return 'text-blue-400';
    return 'text-gray-400';
  };

  if (loading) return <div className="min-h-screen bg-gray-950 text-white flex items-center justify-center"><RefreshCw className="w-8 h-8 animate-spin text-emerald-400" /></div>;

  return (
    <div className="min-h-screen bg-gray-950 text-white p-6">
      <div className="max-w-7xl mx-auto space-y-8">
        <div className="flex items-center justify-between">
          <div>
            <Link href="/founder/tools" className="text-gray-400 hover:text-white flex items-center gap-1 text-sm mb-2"><ArrowLeft className="w-4 h-4" /> Tools</Link>
            <h1 className="text-3xl font-bold flex items-center gap-3"><ListTodo className="w-8 h-8 text-violet-400" /> Task Management Center</h1>
            <p className="text-gray-400 mt-1">Compliance actions, training requirements, and operational follow-ups</p>
          </div>
          <button onClick={loadData} className="px-4 py-2 bg-gray-800 hover:bg-gray-700 rounded-lg flex items-center gap-2 text-sm"><RefreshCw className="w-4 h-4" /> Refresh</button>
        </div>

        {error && <div className="bg-red-900/30 border border-red-700 rounded-lg p-4 flex items-center gap-3"><AlertTriangle className="w-5 h-5 text-red-400" /><span className="text-red-300">{error}</span></div>}

        <div className="grid grid-cols-1 md:grid-cols-4 gap-4">
          <div className="bg-gray-900 border border-gray-800 rounded-lg p-5">
            <div className="text-gray-400 text-sm mb-1 flex items-center gap-1"><ListTodo className="w-4 h-4" /> Total Tasks</div>
            <div className="text-2xl font-bold text-violet-400">{tasks.length}</div>
          </div>
          <div className="bg-gray-900 border border-gray-800 rounded-lg p-5">
            <div className="text-gray-400 text-sm mb-1 flex items-center gap-1"><CircleDot className="w-4 h-4" /> Pending</div>
            <div className="text-2xl font-bold text-amber-400">{tasks.filter(t => t.status === 'pending').length}</div>
          </div>
          <div className="bg-gray-900 border border-gray-800 rounded-lg p-5">
            <div className="text-gray-400 text-sm mb-1 flex items-center gap-1"><Clock className="w-4 h-4" /> In Progress</div>
            <div className="text-2xl font-bold text-blue-400">{tasks.filter(t => t.status === 'in_progress').length}</div>
          </div>
          <div className="bg-gray-900 border border-gray-800 rounded-lg p-5">
            <div className="text-gray-400 text-sm mb-1 flex items-center gap-1"><CheckCircle className="w-4 h-4" /> Completed</div>
            <div className="text-2xl font-bold text-emerald-400">{tasks.filter(t => t.status === 'completed').length}</div>
          </div>
        </div>

        <div className="flex gap-2">
          <button onClick={() => setFilter('all')} className={`px-3 py-1.5 rounded text-sm ${filter === 'all' ? 'bg-violet-600 text-white' : 'bg-gray-800 text-gray-400'}`}><Filter className="w-3 h-3 inline mr-1" />All</button>
          <button onClick={() => setFilter('compliance')} className={`px-3 py-1.5 rounded text-sm ${filter === 'compliance' ? 'bg-violet-600 text-white' : 'bg-gray-800 text-gray-400'}`}>Compliance</button>
          <button onClick={() => setFilter('operations')} className={`px-3 py-1.5 rounded text-sm ${filter === 'operations' ? 'bg-violet-600 text-white' : 'bg-gray-800 text-gray-400'}`}>Operations</button>
        </div>

        <div className="bg-gray-900 border border-gray-800 rounded-lg overflow-hidden">
          <div className="px-6 py-4 border-b border-gray-800"><h2 className="text-lg font-semibold flex items-center gap-2"><ListTodo className="w-5 h-5 text-violet-400" /> Task Queue</h2></div>
          {filteredTasks.length === 0 ? (
            <div className="p-12 text-center text-gray-500"><CheckCircle className="w-12 h-12 mx-auto mb-3 opacity-30" /><p>No tasks. All caught up!</p></div>
          ) : (
            <div className="divide-y divide-gray-800">
              {filteredTasks.map((t) => (
                <div key={t.id} className="px-6 py-4 flex items-center justify-between">
                  <div>
                    <div className="text-white font-medium">{t.title}</div>
                    <div className="text-xs text-gray-500 mt-1">
                      <span className="mr-3">{t.category}</span>
                      {t.assigned_to && <span className="mr-3">→ {t.assigned_to}</span>}
                      {t.due_date && <span>Due: {new Date(t.due_date).toLocaleDateString()}</span>}
                    </div>
                  </div>
                  <span className={`text-xs font-bold uppercase ${priorityColor(t.priority)}`}>{t.priority}</span>
                </div>
              ))}
            </div>
          )}
        </div>
      </div>
    </div>
  );
}
