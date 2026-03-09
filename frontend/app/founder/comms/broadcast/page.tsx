'use client';

import { useEffect, useState } from 'react';
import Link from 'next/link';
import { ArrowLeft, Radio, RefreshCw, AlertTriangle, Send, Users, MessageCircle, Phone } from 'lucide-react';
import { getTelnyxCNAMList, sendFounderCopilotCommand } from '@/services/api';

interface CNAMEntry { phone_number: string; display_name: string; status?: string; }
interface BroadcastRecord { id: string; subject: string; recipients?: number; status: string; sent_at?: string; channel?: string; }

export default function BroadcastPage() {
  const [cnamList, setCnamList] = useState<CNAMEntry[]>([]);
  const [broadcasts, setBroadcasts] = useState<BroadcastRecord[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [subject, setSubject] = useState('');
  const [message, setMessage] = useState('');
  const [channel, setChannel] = useState('sms');
  const [sending, setSending] = useState(false);

  const loadData = async () => {
    setLoading(true);
    setError(null);
    try {
      const cRes = await getTelnyxCNAMList();
      const c = Array.isArray(cRes?.entries) ? cRes.entries : Array.isArray(cRes) ? cRes : [];
      setCnamList(c);
    } catch {
      setCnamList([]);
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => { loadData(); }, []);

  const sendBroadcast = async () => {
    if (!subject.trim() || !message.trim()) return;
    setSending(true);
    setError(null);
    try {
      await sendFounderCopilotCommand({
        command: `Send broadcast: ${subject} - ${message}`,
        context: { type: 'broadcast', channel, subject, message },
      });
      setBroadcasts(prev => [{
        id: `bc-${Date.now()}`,
        subject,
        recipients: cnamList.length,
        status: 'sent',
        sent_at: new Date().toISOString(),
        channel,
      }, ...prev]);
      setSubject('');
      setMessage('');
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Broadcast failed');
    } finally {
      setSending(false);
    }
  };

  if (loading) return <div className="min-h-screen bg-gray-950 text-white flex items-center justify-center"><RefreshCw className="w-8 h-8 animate-spin text-emerald-400" /></div>;

  return (
    <div className="min-h-screen bg-gray-950 text-white p-6">
      <div className="max-w-7xl mx-auto space-y-8">
        <div className="flex items-center justify-between">
          <div>
            <Link href="/founder/comms" className="text-gray-400 hover:text-white flex items-center gap-1 text-sm mb-2"><ArrowLeft className="w-4 h-4" /> Communications</Link>
            <h1 className="text-3xl font-bold flex items-center gap-3"><Radio className="w-8 h-8 text-amber-400" /> Broadcast Center</h1>
            <p className="text-gray-400 mt-1">Mass notification, SMS broadcast, and multi-channel messaging</p>
          </div>
          <button onClick={loadData} className="px-4 py-2 bg-gray-800 hover:bg-gray-700 rounded-lg flex items-center gap-2 text-sm"><RefreshCw className="w-4 h-4" /> Refresh</button>
        </div>

        {error && <div className="bg-red-900/30 border border-red-700 rounded-lg p-4 flex items-center gap-3"><AlertTriangle className="w-5 h-5 text-red-400" /><span className="text-red-300">{error}</span></div>}

        <div className="grid grid-cols-1 md:grid-cols-3 gap-4">
          <div className="bg-gray-900 border border-gray-800 rounded-lg p-5">
            <div className="text-gray-400 text-sm mb-1 flex items-center gap-1"><Phone className="w-4 h-4" /> CNAM Lines</div>
            <div className="text-2xl font-bold text-amber-400">{cnamList.length}</div>
          </div>
          <div className="bg-gray-900 border border-gray-800 rounded-lg p-5">
            <div className="text-gray-400 text-sm mb-1 flex items-center gap-1"><MessageCircle className="w-4 h-4" /> Broadcasts Sent</div>
            <div className="text-2xl font-bold text-blue-400">{broadcasts.length}</div>
          </div>
          <div className="bg-gray-900 border border-gray-800 rounded-lg p-5">
            <div className="text-gray-400 text-sm mb-1 flex items-center gap-1"><Users className="w-4 h-4" /> Total Recipients</div>
            <div className="text-2xl font-bold text-emerald-400">{broadcasts.reduce((a, b) => a + (b.recipients ?? 0), 0)}</div>
          </div>
        </div>

        {/* Compose Broadcast */}
        <div className="bg-gray-900 border border-gray-800 rounded-lg p-6">
          <h2 className="text-lg font-semibold mb-4 flex items-center gap-2"><Send className="w-5 h-5 text-amber-400" /> Compose Broadcast</h2>
          <div className="space-y-4">
            <input placeholder="Subject" value={subject} onChange={(e) => setSubject(e.target.value)}
              className="w-full bg-gray-800 border border-gray-700 rounded px-3 py-2 text-sm text-white" />
            <textarea placeholder="Broadcast message..." value={message} onChange={(e) => setMessage(e.target.value)} rows={4}
              className="w-full bg-gray-800 border border-gray-700 rounded px-4 py-3 text-sm text-white resize-none" />
            <div className="flex items-center gap-4">
              <select value={channel} onChange={(e) => setChannel(e.target.value)}
                className="bg-gray-800 border border-gray-700 rounded px-3 py-2 text-sm text-white">
                <option value="sms">SMS</option>
                <option value="email">Email</option>
                <option value="push">Push Notification</option>
                <option value="all">All Channels</option>
              </select>
              <button onClick={sendBroadcast} disabled={sending || !subject.trim() || !message.trim()}
                className="px-6 py-2 bg-amber-600 hover:bg-amber-500 disabled:opacity-50 rounded-lg flex items-center gap-2 text-sm font-semibold">
                {sending ? <RefreshCw className="w-4 h-4 animate-spin" /> : <Send className="w-4 h-4" />}
                {sending ? 'Sending...' : 'Send Broadcast'}
              </button>
            </div>
          </div>
        </div>

        {/* Broadcast History */}
        {broadcasts.length > 0 && (
          <div className="bg-gray-900 border border-gray-800 rounded-lg overflow-hidden">
            <div className="px-6 py-4 border-b border-gray-800"><h2 className="text-lg font-semibold flex items-center gap-2"><Radio className="w-5 h-5 text-amber-400" /> Broadcast History</h2></div>
            <table className="w-full text-sm">
              <thead className="bg-gray-800/50">
                <tr>
                  <th className="text-left px-6 py-3 text-gray-400 font-medium">Subject</th>
                  <th className="text-left px-6 py-3 text-gray-400 font-medium">Channel</th>
                  <th className="text-left px-6 py-3 text-gray-400 font-medium">Recipients</th>
                  <th className="text-left px-6 py-3 text-gray-400 font-medium">Status</th>
                  <th className="text-left px-6 py-3 text-gray-400 font-medium">Sent</th>
                </tr>
              </thead>
              <tbody className="divide-y divide-gray-800">
                {broadcasts.map((b) => (
                  <tr key={b.id}>
                    <td className="px-6 py-3 text-white">{b.subject}</td>
                    <td className="px-6 py-3 text-gray-400">{b.channel}</td>
                    <td className="px-6 py-3 text-blue-400">{b.recipients}</td>
                    <td className="px-6 py-3 text-emerald-400 font-bold">{b.status}</td>
                    <td className="px-6 py-3 text-gray-400">{b.sent_at ? new Date(b.sent_at).toLocaleString() : '—'}</td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        )}
      </div>
    </div>
  );
}
