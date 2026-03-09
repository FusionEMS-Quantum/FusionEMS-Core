'use client';

import { useState, useRef } from 'react';
import {
  simulateWisconsinNEMSIS,
  validateNEMSISRawXml,
  nemsisCopilotExplain,
} from '@/services/api';

interface ValidationIssue {
  id?: string;
  path: string;
  message: string;
  level: string;
  ui_section?: string;
  suggested_fix?: string;
}

interface CopilotResult {
  summary: string;
  actions: {
    type: string;
    path: string | null;
    ui_section: string | null;
    instruction: string;
  }[];
  confidence: number;
}

function CopilotResultPanel({ result }: { result: CopilotResult }) {
  return (
    <div className="mt-4 border border-orange/30 bg-[#1A1100] p-4 chamfer-4">
      <div className="flex items-center gap-2 mb-3">
        <svg width="20" height="20" viewBox="0 0 24 24" fill="none" className="text-[#FF4D00]" stroke="currentColor" strokeWidth="2">
          <path d="M12 2v4M12 18v4M4.93 4.93l2.83 2.83M16.24 16.24l2.83 2.83M2 12h4M18 12h4M4.93 19.07l2.83-2.83M16.24 7.76l2.83-2.83" />
        </svg>
        <h3 className="text-body uppercase tracking-[0.1em] font-bold text-[#FF4D00]">NEMSIS AI Clinical Expert Analysis</h3>
      </div>
      
      <p className="text-sm text-zinc-100 mb-4">{result.summary}</p>

      {result.actions.length > 0 && (
        <div className="space-y-3">
          <h4 className="text-micro uppercase tracking-wider text-zinc-500">Recommended Actions</h4>
          {result.actions.map((act, i) => (
            <div key={i} className="bg-hud-bg/50 border border-hud-border p-3 chamfer-2">
              <div className="flex items-start gap-3">
                <div className="mt-1 flex-shrink-0">
                  <div className="w-5 h-5  bg-[#FF4D00]/10 border border-orange/40 flex items-center justify-center text-micro text-[#FF4D00]">
                    {i + 1}
                  </div>
                </div>
                <div>
                  <div className="text-xs text-zinc-500 mb-1 font-mono">
                    [{act.type}] {act.ui_section ? `Section: ${act.ui_section}` : ''}
                  </div>
                  <div className="text-sm text-zinc-100">{act.instruction}</div>
                  {act.path && <div className="text-micro text-zinc-500 mt-1 font-mono">{act.path}</div>}
                </div>
              </div>
            </div>
          ))}
        </div>
      )}
      
      <div className="mt-4 pt-3 border-t border-hud-border/30 flex justify-between items-center text-micro text-zinc-500 font-mono">
        <span>Confidence: {(result.confidence * 100).toFixed(0)}%</span>
        <span>Models: gpt-4o / gemini-1.5-pro</span>
      </div>
    </div>
  );
}

export default function NemsisPage() {
  const [issues, setIssues] = useState<ValidationIssue[]>([]);
  const [copilotResult, setCopilotResult] = useState<CopilotResult | null>(null);
  const [loadingCopilot, setLoadingCopilot] = useState(false);
  const [copilotError, setCopilotError] = useState('');
  
  const [isDragging, setIsDragging] = useState(false);
  const [isValidating, setIsValidating] = useState(false);
  const [validationSuccess, setValidationSuccess] = useState<boolean | null>(null);
  const [wisconsinJobs, setWisconsinJobs] = useState<any[]>([]);
  const [isSimulating, setIsSimulating] = useState(false);

  const runWisconsinSimulation = async () => {
    setIsSimulating(true);
    setWisconsinJobs([]);
    try {
      const data = await simulateWisconsinNEMSIS();
      if (data.jobs) setWisconsinJobs(data.jobs);
    } catch (e) {
      console.error("Simulation failed", e);
    } finally {
      setIsSimulating(false);
    }
  };
  const fileInputRef = useRef<HTMLInputElement>(null);

  const handleDragOver = (e: React.DragEvent) => {
    e.preventDefault();
    setIsDragging(true);
  };

  const handleDragLeave = (e: React.DragEvent) => {
    e.preventDefault();
    setIsDragging(false);
  };

  const validateXMLContent = async (xmlContent: string) => {
    setIsValidating(true);
    setValidationSuccess(null);
    setIssues([]);
    setCopilotResult(null);
    setCopilotError('');

    try {
      const data = await validateNEMSISRawXml(xmlContent);
      
      setValidationSuccess(data.valid);
      
      if (data.issues && data.issues.length > 0) {
        setIssues(data.issues);
      }
    } catch (e) {
      console.error(e);
      setValidationSuccess(false);
      setIssues([
        {
          id: "parse-error",
          path: "Document Root",
          message: "Fatal XML Parsing Error: Document cannot be parsed by NEMSIS XSD",
          level: "error",
          ui_section: "Upload Processor",
          suggested_fix: "Ensure valid XML syntax before schematron validation."
        }
      ]);
    } finally {
      setIsValidating(false);
    }
  };

  const processFile = (file: File) => {
    if (!file) return;
    const reader = new FileReader();
    reader.onload = async (e) => {
      const content = e.target?.result as string;
      if (content) {
        await validateXMLContent(content);
      }
    };
    reader.readAsText(file);
  };

  const handleDrop = (e: React.DragEvent) => {
    e.preventDefault();
    setIsDragging(false);
    if (e.dataTransfer.files && e.dataTransfer.files[0]) {
      processFile(e.dataTransfer.files[0]);
    }
  };

  async function explainWithCopilot() {
    setLoadingCopilot(true);
    setCopilotResult(null);
    setCopilotError('');
    
    try {
      const json = await nemsisCopilotExplain({
        issues,
        context: { version: "3.5.1", state: "WI" }
      });
      setCopilotResult(json);
    } catch (e) {
      setCopilotError(e instanceof Error ? e.message : 'Copilot explain failed');
    } finally {
      setLoadingCopilot(false);
    }
  }

  return (
    <div className="p-5 min-h-screen">
      <div className="hud-rail pb-3 mb-6">
        <div className="micro-caps mb-1">Compliance Engine</div>
        <h1 className="text-h2 font-bold text-zinc-100">NEMSIS v3.5.1 Certification Readiness</h1>
        <p className="text-body text-zinc-500 mt-1">Real-time deep XML interrogation with AI Copilot mapping assistance.</p>
      </div>

      <div className="grid grid-cols-1 lg:grid-cols-3 gap-6">
        <div className="lg:col-span-2 space-y-6">
          
          {/* DRAG AND DROP ZONE */}
          <div 
             onDragOver={handleDragOver}
             onDragLeave={handleDragLeave}
             onDrop={handleDrop}
             className={`border-2 border-dashed chamfer-8 p-10 transition-all duration-fast text-center relative overflow-hidden group
               ${isDragging ? 'border-orange bg-[#FF4D00]/5' : 'border-border-DEFAULT bg-[#0A0A0B]'}
             `}
          >
            <div className="absolute inset-0 bg-gradient-to-br from-bg-panel via-transparent to-bg-panel opacity-50 z-0"></div>
            
            <input 
               type="file" 
               accept=".xml" 
               ref={fileInputRef}
               className="hidden" 
               onChange={(e) => {
                 if (e.target.files && e.target.files[0]) {
                   processFile(e.target.files[0]);
                 }
               }} 
            />

            <div className="relative z-10 flex flex-col items-center justify-center space-y-4">
              <div className={`w-16 h-16  flex items-center justify-center transition-colors ${isDragging ? 'bg-[#FF4D00] text-black' : 'bg-hud-bg border border-border-DEFAULT text-zinc-500'}`}>
                {isValidating ? (
                   <svg className="animate-spin h-8 w-8 text-[#FF4D00]" xmlns="http://www.w3.org/2000/svg" fill="none" viewBox="0 0 24 24">
                     <circle className="opacity-25" cx="12" cy="12" r="10" stroke="currentColor" strokeWidth="4"></circle>
                     <path className="opacity-75" fill="currentColor" d="M4 12a8 8 0 018-8V0C5.373 0 0 5.373 0 12h4zm2 5.291A7.962 7.962 0 014 12H0c0 3.042 1.135 5.824 3 7.938l3-2.647z"></path>
                   </svg>
                ) : (
                   <svg width="32" height="32" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
                     <path d="M21 15v4a2 2 0 0 1-2 2H5a2 2 0 0 1-2-2v-4"></path>
                     <polyline points="17 8 12 3 7 8"></polyline>
                     <line x1="12" y1="3" x2="12" y2="15"></line>
                   </svg>
                )}
              </div>
              <div>
                <h3 className="text-h4 font-bold text-zinc-100">Upload Core NEMSIS XML</h3>
                <p className="text-sm text-zinc-500 mt-1 max-w-md mx-auto">
                  Drag and drop agency ePCR or state export .xml files here for direct validator parsing and live AI compliance mapping.
                </p>
              </div>
              <div className="flex gap-4 pt-2">
                <button 
                  onClick={() => fileInputRef.current?.click()}
                  className="btn-quantum-secondary"
                  disabled={isValidating}
                >
                  Browse Files
                </button>
              </div>
            </div>
          </div>

          
          {/* WISCONSIN PILOT ZONE */}
          <div className="bg-[#0A0A0B] border border-border-DEFAULT chamfer-8 shadow-elevation-1 p-6">
             <div className="flex items-center justify-between mb-4">
               <div>
                  <h3 className="text-h4 font-bold text-zinc-100">Wisconsin Pilot Dry-Run</h3>
                  <p className="text-xs text-zinc-500 mt-1">Simulate 5 concurrent state exports to database</p>
               </div>
               <button 
                  onClick={runWisconsinSimulation}
                  disabled={isSimulating}
                  className="btn-quantum-ghost text-xs border border-orange text-[#FF4D00]"
               >
                 {isSimulating ? 'Deploying to DB...' : 'Run Simulation Batch'}
               </button>
             </div>
             
             {wisconsinJobs.length > 0 && (
               <div className="mt-4 space-y-2 animate-in fade-in slide-in-from-top-4 duration-300">
                 {wisconsinJobs.map((j: any, idx: number) => (
                   <div key={idx} className="flex justify-between items-center bg-black/30 p-2 chamfer-2 border border-border-DEFAULT text-xs">
                     <span className="font-mono text-green-400">SUCCESS</span>
                     <span className="text-zinc-500">Job {j.id.substring(0, 8)}</span>
                     <span className="text-zinc-100">{j.data?.rules_passed} Rules Checked</span>
                     <span className="font-mono text-zinc-500">Inserted into RDS</span>
                   </div>
                 ))}
               </div>
             )}
          </div>
          
          {/* RESULTS ZONE */}
          {(validationSuccess !== null || issues.length > 0) && (
            <div className="bg-[#0A0A0B] border border-border-DEFAULT chamfer-8 shadow-elevation-1 p-6 animate-in fade-in slide-in-from-bottom-4 duration-300">
              
              {/* Header Status */}
              <div className="flex items-center justify-between mb-4 border-b border-border-DEFAULT pb-4">
                <div className="flex items-center gap-4">
                   {validationSuccess ? (
                     <div className="w-10 h-10  bg-green-500/20 border border-green-500/50 flex items-center justify-center text-green-400">
                       <svg className="w-6 h-6" fill="none" viewBox="0 0 24 24" stroke="currentColor"><path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M5 13l4 4L19 7"/></svg>
                     </div>
                   ) : (
                     <div className="w-10 h-10  bg-red-500/20 border border-red-500/50 flex items-center justify-center text-red-400">
                       <svg className="w-6 h-6" fill="none" viewBox="0 0 24 24" stroke="currentColor"><path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M6 18L18 6M6 6l12 12"/></svg>
                     </div>
                   )}
                   <div>
                     <h2 className="text-h4 font-bold text-zinc-100">
                       {validationSuccess ? 'Schema Validation Passed' : 'Validation Errors Identified'}
                     </h2>
                     <p className="text-xs text-zinc-500 mt-0.5">XSD 3.5.1 and Schematron Pipeline</p>
                   </div>
                </div>

                {!validationSuccess && issues.length > 0 && (
                  <button
                    onClick={explainWithCopilot}
                    disabled={loadingCopilot}
                    className="btn-quantum-primary text-xs shrink-0 relative overflow-hidden"
                  >
                    <span className="relative z-10 flex items-center gap-2">
                       <svg className="w-4 h-4" fill="none" viewBox="0 0 24 24" stroke="currentColor"><path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M13 10V3L4 14h7v7l9-11h-7z"/></svg>
                       {loadingCopilot ? 'AI Analyzing Payload...' : 'Explain All with Copilot'}
                    </span>
                  </button>
                )}
              </div>
              
              {copilotError && (
                <div className="text-red-500 text-sm mb-4 px-3 py-2 bg-red-500/10 border border-red-500/20 chamfer-2">
                  {copilotError}
                </div>
              )}

              {copilotResult && <CopilotResultPanel result={copilotResult} />}

              {!validationSuccess && issues.length > 0 && (
                <div className="mt-6 space-y-3">
                   <h3 className="micro-caps">Raw Output ({issues.length} {issues.length === 1 ? 'Rule' : 'Rules'})</h3>
                  {issues.map(issue => (
                    <div key={issue.id} className="border border-hud-border/40 p-3 bg-hud-bg chamfer-2">
                      <div className="flex gap-2 items-start">
                        <span className={`px-1.5 py-0.5 chamfer-4 text-[9px] font-mono uppercase mt-0.5 ${issue.level === 'error' ? 'bg-red-500/20 text-red-400' : 'bg-[#FF4D00]/20 text-[#FF4D00]'}`}>
                          {issue.level}
                        </span>
                        <div>
                          <div className="font-mono text-xs text-zinc-100">{issue.message}</div>
                          <div className="font-mono text-micro text-zinc-500 mt-1 break-all bg-black/40 p-1 px-2 chamfer-4">
                            {issue.path}
                          </div>
                        </div>
                      </div>
                    </div>
                  ))}
                </div>
              )}
            </div>
          )}

        </div>

        <div className="space-y-6">
          <div className="bg-[#0A0A0B] border border-border-DEFAULT chamfer-8 p-5 shadow-elevation-1 sticky top-6">
            <h3 className="text-sm font-bold text-zinc-400 uppercase tracking-wider mb-4">Certification Sequence</h3>
            
            <div className="absolute top-5 right-5">
              <span className="relative flex h-3 w-3">
                <span className="animate-ping absolute inline-flex h-full w-full  bg-green-400 opacity-75"></span>
                <span className="relative inline-flex  h-3 w-3 bg-green-500"></span>
              </span>
            </div>

            <ul className="space-y-5 text-sm text-zinc-500 relative">
              <div className="absolute left-3 top-2 bottom-5 w-px bg-border-DEFAULT"></div>
              
              <li className="flex items-start gap-3 relative z-10">
                <div className="bg-green-500 text-black  w-6 h-6 flex items-center justify-center shrink-0 mt-0.5 shadow-[0_0_10px_rgba(74,222,128,0.3)]">
                  <svg className="w-4 h-4" fill="none" viewBox="0 0 24 24" stroke="currentColor"><path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M5 13l4 4L19 7"/></svg>
                </div>
                <div>
                  <strong className="text-zinc-100 block">XSD Validation Engine</strong>
                  <span className="text-body">Strict schema compliance checks</span>
                </div>
              </li>
              <li className="flex items-start gap-3 relative z-10">
                <div className="bg-green-500 text-black  w-6 h-6 flex items-center justify-center shrink-0 mt-0.5 shadow-[0_0_10px_rgba(74,222,128,0.3)]">
                  <svg className="w-4 h-4" fill="none" viewBox="0 0 24 24" stroke="currentColor"><path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M5 13l4 4L19 7"/></svg>
                </div>
                <div>
                  <strong className="text-zinc-100 block">Schematron Business Rules</strong>
                  <span className="text-body">State & National demographic tracking</span>
                </div>
              </li>
              <li className="flex items-start gap-3 relative z-10">
                <div className="bg-[#FF4D00] text-black  w-6 h-6 flex items-center justify-center shrink-0 mt-0.5 shadow-[0_0_10px_rgba(255,107,26,0.3)]">
                   <svg className="w-4 h-4" fill="none" viewBox="0 0 24 24" stroke="currentColor"><path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M13 10V3L4 14h7v7l9-11h-7z"/></svg>
                </div>
                <div>
                  <strong className="text-[#FF4D00] block">Mission Control AI Copilot</strong>
                  <span className="text-body">Deep context translation mapped to your inputs</span>
                </div>
              </li>
              <li className="flex items-start gap-3 relative z-10 opacity-50">
                <div className="bg-[#0A0A0B] border-2 border-border-DEFAULT  w-6 h-6 flex items-center justify-center shrink-0 mt-0.5">
                   <div className="w-2 h-2  bg-border-DEFAULT"></div>
                </div>
                <div>
                  <strong className="text-zinc-100 block">Production Export Pipeline</strong>
                  <span className="text-body">Awaiting green light state clearance</span>
                </div>
              </li>
            </ul>
          </div>
        </div>
      </div>
    </div>
  );
}
