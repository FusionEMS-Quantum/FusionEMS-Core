"use client";

import React, { useState, useRef, useEffect } from 'react';
import { motion, AnimatePresence } from 'framer-motion';
import { Bot, Send, X, User } from 'lucide-react';

const uuidv4 = (): string => crypto.randomUUID();

interface Message {
  id: string;
  sender: 'user' | 'ai';
  type: 'text' | 'code' | 'status_update';
  content: string;
  timestamp: string;
}

export default function FounderCopilotPanel({ isOpen, onClose }: { isOpen: boolean; onClose: () => void; }) {
  const [messages, setMessages] = useState<Message[]>([]);
  const [input, setInput] = useState('');
  const [isThinking, setIsThinking] = useState(false);
  const messagesEndRef = useRef<HTMLDivElement>(null);

  const scrollToBottom = () => {
    messagesEndRef.current?.scrollIntoView({ behavior: "smooth" });
  };

  useEffect(scrollToBottom, [messages]);

  const handleSend = async () => {
    if (!input.trim()) return;

    const userMessage: Message = {
      id: uuidv4(),
      sender: 'user',
      type: 'text',
      content: input,
      timestamp: new Date().toISOString(),
    };
    setMessages(prev => [...prev, userMessage]);
    setInput('');
    setIsThinking(true);

    try {
      const res = await fetch('/api/founder/copilot/command', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ prompt: input, session_id: 'founder_main' }),
      });
      const data = await res.json();
      
      const aiMessage: Message = {
        id: uuidv4(),
        sender: 'ai',
        type: data.response_type,
        content: data.content,
        timestamp: data.timestamp,
      };
      setMessages(prev => [...prev, aiMessage]);

    } catch (error) {
      const errorMessage: Message = {
        id: uuidv4(),
        sender: 'ai',
        type: 'text',
        content: '[ERROR] Connection to AI core failed. Please check backend services.',
        timestamp: new Date().toISOString(),
      };
      setMessages(prev => [...prev, errorMessage]);
    } finally {
      setIsThinking(false);
    }
  };

  return (
    <AnimatePresence>
      {isOpen && (
        <motion.div
          initial={{ opacity: 0, y: 50 }}
          animate={{ opacity: 1, y: 0 }}
          exit={{ opacity: 0, y: 50 }}
          transition={{ duration: 0.3, ease: 'easeInOut' }}
          className="fixed bottom-10 right-10 z-[100] w-[90vw] max-w-2xl h-[70vh] bg-[#0D1017] border border-blue-500/30 rounded-2xl shadow-2xl shadow-blue-900/20 flex flex-col overflow-hidden"
        >
          {/* Header */}
          <div className="bg-blue-900/20 border-b border-blue-500/30 p-4 flex justify-between items-center shrink-0">
            <div className="flex items-center gap-3">
              <Bot className="w-6 h-6 text-blue-400 animate-pulse" />
              <div>
                <h3 className="text-blue-300 font-bold tracking-widest uppercase">FOUNDER&apos;S COPILOT</h3>
                <p className="text-blue-500/60 text-xs font-mono">Sovereign AI Command Interface</p>
              </div>
            </div>
            <button onClick={onClose} className="text-gray-400 hover:text-white transition-colors">
              <X className="w-6 h-6" />
            </button>
          </div>

          {/* Messages Area */}
          <div className="flex-1 p-6 overflow-y-auto space-y-6">
            {messages.map(msg => (
              <div key={msg.id} className={`flex items-start gap-3 ${msg.sender === 'user' ? 'justify-end' : ''}`}>
                {msg.sender === 'ai' && <Bot className="w-5 h-5 text-blue-500 shrink-0 mt-1" />}
                <div className={`w-full max-w-lg p-4 rounded-xl ${msg.sender === 'user' ? 'bg-blue-900/40' : 'bg-gray-800/30'}`}>
                  {msg.type === 'code' ? (
                    <pre className="bg-black/50 p-3 rounded-md text-xs text-cyan-300 font-mono whitespace-pre-wrap overflow-x-auto"><code>{msg.content}</code></pre>
                  ) : msg.type === 'status_update' ? (
                    <p className="text-yellow-300 text-sm">{msg.content}</p>
                  ) : (
                    <p className="text-gray-300 text-sm whitespace-pre-wrap">{msg.content}</p>
                  )}
                  <p className="text-right text-xs text-gray-600 mt-2 font-mono">{new Date(msg.timestamp).toLocaleTimeString()}</p>
                </div>
                {msg.sender === 'user' && <User className="w-5 h-5 text-gray-500 shrink-0 mt-1" />}
              </div>
            ))}
            {isThinking && (
              <div className="flex items-start gap-3">
                <Bot className="w-5 h-5 text-blue-500 shrink-0 mt-1 animate-pulse" />
                <div className="w-full max-w-lg p-4 rounded-xl bg-gray-800/30">
                  <p className="text-gray-400 text-sm italic animate-pulse">Processing command...</p>
                </div>
              </div>
            )}
            <div ref={messagesEndRef} />
          </div>

          {/* Input */}
          <div className="p-4 border-t border-blue-500/30 bg-black/30">
            <div className="relative">
              <input
                type="text"
                value={input}
                onChange={(e) => setInput(e.target.value)}
                onKeyPress={(e) => e.key === 'Enter' && handleSend()}
                placeholder="Ask AI to build, fix, or give status..."
                className="w-full bg-[#07090D] border border-gray-700 rounded-lg pl-4 pr-12 py-3 text-sm text-gray-200 focus:outline-none focus:border-blue-500/50 font-mono"
              />
              <button onClick={handleSend} className="absolute right-3 top-1/2 -translate-y-1/2 text-blue-500 hover:text-blue-300 transition-colors">
                <Send className="w-5 h-5" />
              </button>
            </div>
          </div>
        </motion.div>
      )}
    </AnimatePresence>
  );
}
