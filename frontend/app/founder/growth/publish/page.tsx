'use client';

import { useState } from 'react';

export default function PublishingControlCenterPage() {
  const [posts] = useState([
    { id: 1, platform: 'LinkedIn', status: 'Queued', date: 'Today, 2:00 PM', content: 'Did you know standard EMS agencies lose 30% to bad billing? Here is how we fix it...' },
    { id: 2, platform: 'X', status: 'Draft', date: 'Unscheduled', content: 'Our new deployment engine is live. Start your trial now. #EMS #Fire' },
    { id: 3, platform: 'Email', status: 'Sent', date: 'Yesterday, 9:00 AM', content: 'Welcome to your FusionEMS ROI report.' },
  ]);

  return (
    <div className="p-8 text-white">
      <h1 className="text-3xl font-black mb-4">Publishing Control Center</h1>
      <p className="text-white/60 mb-8">Manage AI-generated campaigns, approve drafts, and track post performance.</p>

      <div className="flex gap-4 mb-6">
        <button className="bg-[var(--color-bg-raised)] hover:bg-[var(--color-bg-overlay)] text-white font-bold py-2 px-4 text-sm">All Platforms</button>
        <button className="border border-white/20 hover:bg-white/5 text-white py-2 px-4 text-sm">LinkedIn</button>
        <button className="border border-white/20 hover:bg-white/5 text-white py-2 px-4 text-sm">X</button>
        <button className="border border-white/20 hover:bg-white/5 text-white py-2 px-4 text-sm">Email Sequences</button>
      </div>

      <div className="bg-[var(--color-bg-base)] border border-white/10 overflow-hidden">
        <table className="w-full text-left">
          <thead className="bg-[var(--color-bg-panel)] border-b border-white/10">
            <tr>
              <th className="p-4 text-xs tracking-wider text-white/50 uppercase font-medium">Platform</th>
              <th className="p-4 text-xs tracking-wider text-white/50 uppercase font-medium">Content Preview</th>
              <th className="p-4 text-xs tracking-wider text-white/50 uppercase font-medium">Schedule</th>
              <th className="p-4 text-xs tracking-wider text-white/50 uppercase font-medium">Status</th>
              <th className="p-4 text-xs tracking-wider text-white/50 uppercase font-medium">Actions</th>
            </tr>
          </thead>
          <tbody className="divide-y divide-white/5">
            {posts.map((post) => (
              <tr key={post.id} className="hover:bg-[var(--color-bg-panel)]/50 transition-colors">
                <td className="p-4">
                  <span className={`inline-block px-2 py-1 text-xs font-bold ${
                    post.platform === 'LinkedIn' ? 'bg-blue-900/50 text-[var(--color-status-info)]' :
                    post.platform === 'X' ? 'bg-[var(--color-bg-raised)] text-white' :
                    'bg-purple-900/50 text-purple-400'
                  }`}>
                    {post.platform}
                  </span>
                </td>
                <td className="p-4 text-sm text-white/80 max-w-md truncate">{post.content}</td>
                <td className="p-4 text-sm text-white/60">{post.date}</td>
                <td className="p-4">
                  <span className={`inline-flex items-center gap-1.5 text-xs font-bold ${
                    post.status === 'Queued' ? 'text-[var(--q-yellow)]' :
                    post.status === 'Sent' ? 'text-[var(--color-status-active)]' :
                    'text-white/40'
                  }`}>
                    <span className={`w-1.5 h-1.5 rounded-full ${
                      post.status === 'Queued' ? 'bg-amber-400' :
                      post.status === 'Sent' ? 'bg-emerald-400' :
                      'bg-white/40'
                    }`} />
                    {post.status}
                  </span>
                </td>
                <td className="p-4">
                  <button className="text-[var(--color-status-info)] hover:text-[var(--color-status-info)] text-sm font-medium mr-3">Edit</button>
                  {post.status === 'Draft' && (
                    <button className="text-[var(--color-status-active)] hover:text-[var(--color-status-active)] text-sm font-medium">Approve</button>
                  )}
                </td>
              </tr>
            ))}
          </tbody>
        </table>
      </div>
    </div>
  );
}
