"use client"

import React from "react"

export interface AIExplanationProps {
  title: string
  severity: "BLOCKING" | "HIGH" | "MEDIUM" | "LOW" | "INFORMATIONAL"
  source: "AI REVIEW" | "RULE + AI" | "PROVIDER RESPONSE" | "HUMAN NOTE"
  whatIsWrong: string
  whyItMatters: string
  whatYouShouldDo: string
  domainContext: string
  humanReview: "REQUIRED" | "RECOMMENDED" | "SAFE TO AUTO-PROCESS"
  confidence: "HIGH" | "MEDIUM" | "LOW"
}

export function AIExplanationCard({ data }: { data: AIExplanationProps }) {
  const getSeverityColor = (sev: string) => {
    switch (sev) {
      case "BLOCKING": return "bg-red-100 text-red-800 border-red-300"
      case "HIGH": return "bg-orange-100 text-orange-800 border-orange-300"
      case "MEDIUM": return "bg-yellow-100 text-yellow-800 border-yellow-300"
      default: return "bg-slate-100 text-slate-800 border-slate-300"
    }
  }

  const getConfidenceBadge = (conf: string) => {
    if (conf === "LOW") return "bg-yellow-100 text-yellow-800 border border-yellow-300"
    if (conf === "MEDIUM") return "bg-blue-100 text-blue-800 border border-blue-300"
    return "bg-green-100 text-green-800 border border-green-300"
  }

  return (
    <div className="border border-slate-200 shadow-sm rounded-lg overflow-hidden bg-white text-slate-900 text-sm">
      {/* Header */}
      <div className={`px-4 py-3 border-b flex justify-between items-center ${getSeverityColor(data.severity)}`}>
        <div className="font-bold flex items-center space-x-2">
          <span>{data.title}</span>
          <span className="px-2 py-0.5 text-xs rounded bg-white bg-opacity-50">
            {data.severity}
          </span>
        </div>
        <div className={`px-2 py-0.5 text-xs rounded font-bold ${getConfidenceBadge(data.confidence)}`}>
          CONFIDENCE: {data.confidence}
        </div>
      </div>

      <div className="p-4 space-y-4">
        <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
          <div>
            <div className="text-xs font-bold text-slate-500 uppercase">What is wrong</div>
            <div className="mt-1 text-slate-800">{data.whatIsWrong}</div>
          </div>
          <div>
            <div className="text-xs font-bold text-slate-500 uppercase">Why it matters</div>
            <div className="mt-1 text-slate-800">{data.whyItMatters}</div>
          </div>
        </div>

        <div className="bg-slate-50 p-3 rounded border border-slate-100">
          <div className="text-xs font-bold text-slate-500 uppercase mb-1">What you should do</div>
          <div className="font-medium text-slate-900">{data.whatYouShouldDo}</div>
        </div>

        <div className="flex justify-between items-end pt-2 border-t border-slate-100 text-xs text-slate-500">
          <div>
            <strong>SOURCE:</strong> {data.source} <br/>
            <strong>CONTEXT:</strong> {data.domainContext}
          </div>
          <div className={`font-bold ${data.humanReview === 'REQUIRED' ? 'text-red-600' : 'text-slate-500'}`}>
            REVIEW: {data.humanReview}
          </div>
        </div>
      </div>
    </div>
  )
}
