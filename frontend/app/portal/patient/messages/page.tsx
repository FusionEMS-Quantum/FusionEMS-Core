'use client';

import React, { useEffect, useState } from 'react';
import { QuantumCardSkeleton, QuantumEmptyState } from '@/components/ui';
import { getPortalMessages, sendPortalMessage } from '@/services/api';

interface Message {
  id: string;
  subject: string;
  body: string;
  direction: 'inbound' | 'outbound';
  created_at: string;
}

export default function PatientMessagesPage() {
  const [messages, setMessages] = useState<Message[]>([]);
  const [loading, setLoading] = useState(true);
  const [subject, setSubject] = useState('');
  const [body, setBody] = useState('');
  const [sending, setSending] = useState(false);

  const fetchMessages = async () => {
    try {
      const data = await getPortalMessages();
      setMessages(data as Message[]);
    } catch {
      setMessages([]);
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    fetchMessages();
  }, []);

  const handleSend = async () => {
    if (!subject.trim() || !body.trim()) return;
    setSending(true);
    try {
      await sendPortalMessage({ subject: subject.trim(), body: body.trim() });
      setSubject('');
      setBody('');
      await fetchMessages();
    } catch (err) {
      console.error('Failed to send message', err);
    } finally {
      setSending(false);
    }
  };

  return (
    <div className="max-w-3xl mx-auto py-8 px-4">
      <h1 className="text-2xl font-bold text-zinc-100 mb-1">Messages</h1>
      <p className="text-sm text-zinc-500 mb-6">
        Communicate with your provider about billing questions, records requests, or general inquiries.
      </p>

      {/* Compose */}
      <div className="bg-[#0A0A0B] border border-[var(--color-border-default)] chamfer-8 p-5 mb-6">
        <div className="text-micro uppercase tracking-widest text-zinc-500 mb-3">New Message</div>
        <input
          type="text"
          placeholder="Subject"
          value={subject}
          onChange={(e) => setSubject(e.target.value)}
          className="w-full bg-black border border-[var(--color-border-default)] text-sm text-zinc-100 px-3 py-2 mb-3  focus:border-brand-orange/50 outline-none"
        />
        <textarea
          placeholder="Type your message..."
          value={body}
          onChange={(e) => setBody(e.target.value)}
          rows={4}
          className="w-full bg-black border border-[var(--color-border-default)] text-sm text-zinc-100 px-3 py-2 mb-3  resize-none focus:border-brand-orange/50 outline-none"
        />
        <button
          onClick={handleSend}
          disabled={sending || !subject.trim() || !body.trim()}
          className="quantum-btn disabled:opacity-40 disabled:cursor-not-allowed"
        >
          {sending ? 'Sending...' : 'Send Message'}
        </button>
      </div>

      {/* Message list */}
      {loading ? (
        <div className="space-y-3">
          <QuantumCardSkeleton />
          <QuantumCardSkeleton />
        </div>
      ) : messages.length === 0 ? (
        <QuantumEmptyState
          title="No messages"
          description="You have no messages yet. Use the form above to start a conversation."
          icon="mail"
        />
      ) : (
        <div className="space-y-3">
          {messages.map((msg) => (
            <div
              key={msg.id}
              className="bg-[#0A0A0B] border border-[var(--color-border-default)] chamfer-8 p-4"
            >
              <div className="flex items-center justify-between mb-2">
                <div className="flex items-center gap-2">
                  <span
                    className={`text-micro font-bold uppercase ${
                      msg.direction === 'outbound' ? 'text-brand-orange' : 'text-zinc-500'
                    }`}
                  >
                    {msg.direction === 'outbound' ? 'You' : 'Provider'}
                  </span>
                  <span className="text-sm font-semibold text-zinc-100">{msg.subject}</span>
                </div>
                <span className="text-micro text-zinc-500">
                  {new Date(msg.created_at).toLocaleDateString()}
                </span>
              </div>
              <div className="text-sm text-zinc-400 whitespace-pre-wrap">{msg.body}</div>
            </div>
          ))}
        </div>
      )}
    </div>
  );
}
