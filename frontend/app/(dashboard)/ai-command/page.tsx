"use client"

import React, { useEffect, useState } from "react"

// Types
interface AIHealthMetrics {
  health_score: number
  disabled_workflows: number
  low_confidence_count: number
  review_queue_count: number
  failed_runs_count: number
  recent_reviews_required: Array<{
    run_id: number
    correlation_id: string
    summary: string
    use_case: string
  }>
}

export default function AICommandCenter() {
  const [metrics, setMetrics] = useState<AIHealthMetrics | null>(null)
  const [loading, setLoading] = useState<boolean>(true)

  useEffect(() => {
    // In actual implementation, use RTK Query or SWR centralized API
    async function fetchMetrics() {
      try {
        const response = await fetch("/api/v1/ai/command-center/metrics")
        if (response.ok) {
          const data = await response.json()
          setMetrics(data)
        } else {
          // Dummy fallback for isolated views or demo fallback
          setMetrics({
            health_score: 87.5,
            disabled_workflows: 2,
            low_confidence_count: 14,
            review_queue_count: 5,
            failed_runs_count: 3,
            recent_reviews_required: [
              {
                run_id: 101,
                correlation_id: "REQ-9981",
                summary: "Possible payer mismatch in claims reasoning.",
                use_case: "Billing Claim Scrubbing"
              },
              {
                run_id: 105,
                correlation_id: "REQ-9993",
                summary: "Suggested collections escalation is high-risk.",
                use_case: "Collections Escalation"
              }
            ]
          })
        }
      } catch (err) {
        console.error("Failed to load AI metrics", err)
      } finally {
        setLoading(false)
      }
    }
    fetchMetrics()
  }, [])

  if (loading) {
    return <div className="p-8 text-gray-500">Loading AI Command Center...</div>
  }

  if (!metrics) {
    return <div className="p-8 text-red-500">Failed to launch AI Governance state. Fallback required.</div>
  }

  return (
    <div className="p-8 max-w-7xl mx-auto space-y-6">
      <div className="flex justify-between items-center">
        <div>
          <h1 className="text-3xl font-bold tracking-tight text-slate-900">AI Command Center</h1>
          <p className="text-slate-500 mt-2">Governance, Explainability, and Workflow Override</p>
        </div>
        <div className="text-right">
          <div className={`text-4xl font-black ${metrics.health_score > 90 ? 'text-green-600' : 'text-yellow-600'}`}>
            {metrics.health_score}%
          </div>
          <p className="text-xs uppercase tracking-widest font-semibold text-slate-500">Platform Health</p>
        </div>
      </div>

      {/* TOP WIDGETS */}
      <div className="grid grid-cols-1 md:grid-cols-4 gap-4">
        <WidgetCard 
          title="Review Queue" 
          value={metrics.review_queue_count} 
          color="BLUE"
          sub="Requires human approval"
        />
        <WidgetCard 
          title="Low Confidence" 
          value={metrics.low_confidence_count} 
          color="YELLOW"
          sub="Flagged AI Outputs"
        />
        <WidgetCard 
          title="Disabled Workflows" 
          value={metrics.disabled_workflows} 
          color="GRAY"
          sub="Explicitly isolated"
        />
        <WidgetCard 
          title="Failures" 
          value={metrics.failed_runs_count} 
          color="RED"
          sub="Blocking errors"
        />
      </div>

      {/* HUMAN OVERRIDE ACTIONS */}
      <div className="mt-8 border rounded-lg shadow-sm bg-white overflow-hidden">
        <div className="bg-slate-50 px-6 py-4 border-b">
          <h2 className="text-lg font-bold text-slate-800">Action Required: Human Review Queue</h2>
        </div>
        <div className="divide-y">
          {metrics.recent_reviews_required.length === 0 ? (
            <div className="p-6 text-slate-500 text-center">No high-risk outputs pending review.</div>
          ) : (
            metrics.recent_reviews_required.map(run => (
              <ReviewRow key={run.run_id} request={run} />
            ))
          )}
        </div>
      </div>
    </div>
  )
}

function WidgetCard({ title, value, color, sub }: { title: string, value: number, color: string, sub: string }) {
  const colorMap: Record<string, string> = {
    RED: "bg-red-50 text-red-700 border-red-200",
    ORANGE: "bg-orange-50 text-orange-700 border-orange-200",
    YELLOW: "bg-yellow-50 text-yellow-700 border-yellow-200",
    BLUE: "bg-blue-50 text-blue-700 border-blue-200",
    GREEN: "bg-green-50 text-green-700 border-green-200",
    GRAY: "bg-slate-50 text-slate-700 border-slate-200"
  }

  return (
    <div className={`border rounded-lg p-5 flex flex-col justify-between ${colorMap[color] || colorMap.GRAY}`}>
      <div className="text-sm font-bold uppercase tracking-wider opacity-80">{title}</div>
      <div className="text-4xl font-black mt-2">{value}</div>
      <div className="mt-2 text-xs opacity-80">{sub}</div>
    </div>
  )
}

function ReviewRow({ request }: { request: any }) {
  return (
    <div className="p-6 flex flex-col md:flex-row justify-between items-start md:items-center gap-4 hover:bg-slate-50 transition">
      <div>
        <div className="text-xs font-bold text-blue-600 mb-1">{request.use_case}</div>
        <div className="text-sm font-semibold text-slate-900 mb-1">WHAT HAPPENED:</div>
        <p className="text-slate-700 text-sm max-w-2xl">{request.summary}</p>
        <div className="mt-3 inline-block px-2 py-1 text-xs bg-slate-200 rounded text-slate-800 font-mono">
          REF: {request.correlation_id}
        </div>
      </div>
      <div className="flex gap-2 w-full md:w-auto">
        <button className="px-4 py-2 bg-white border border-slate-300 rounded shadow-sm text-sm font-bold text-slate-700 hover:bg-slate-50">
          Reject AI
        </button>
        <button className="px-4 py-2 bg-blue-600 rounded shadow-sm text-sm font-bold text-white hover:bg-blue-700">
          Manual Takeover
        </button>
      </div>
    </div>
  )
}
