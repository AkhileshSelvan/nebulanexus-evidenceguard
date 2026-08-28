import { useState, useEffect } from "react";

const STAGES = [
  { id: "ingest", label: "Ingesting Documents", duration: 800 },
  { id: "ocr", label: "Extracting Text (OCR)", duration: 1500 },
  { id: "forensics", label: "Running Image Forensics", duration: 2000 },
  { id: "metadata", label: "Analyzing Metadata", duration: 1000 },
  { id: "consistency", label: "Checking Consistency", duration: 1200 },
  { id: "risk", label: "Aggregating Risk Score", duration: 800 },
];

export function ProcessingScreen() {
  const [currentStageIndex, setCurrentStageIndex] = useState(0);

  useEffect(() => {
    let timeout: ReturnType<typeof setTimeout>;
    
    if (currentStageIndex < STAGES.length - 1) {
      // Move to next stage after simulated duration
      timeout = setTimeout(() => {
        setCurrentStageIndex(prev => prev + 1);
      }, STAGES[currentStageIndex].duration);
    }

    return () => clearTimeout(timeout);
  }, [currentStageIndex]);

  const progressPercentage = Math.round(((currentStageIndex + 0.5) / STAGES.length) * 100);

  return (
    <div className="flex flex-col items-center justify-center min-h-[60vh] max-w-md mx-auto w-full animate-fade-in">
      <div className="relative w-32 h-32 mb-8 flex items-center justify-center">
        {/* Animated outer ring */}
        <div className="absolute inset-0 rounded-full border-4 border-slate-100"></div>
        <div className="absolute inset-0 rounded-full border-4 border-guard-500 border-t-transparent animate-spin"></div>
        
        {/* Pulse effect */}
        <div className="absolute inset-0 rounded-full bg-guard-100 animate-pulse-ring"></div>
        
        {/* Icon */}
        <svg className="w-10 h-10 text-guard-600 relative z-10" fill="none" viewBox="0 0 24 24" stroke="currentColor">
          <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={1.5} d="M9 12l2 2 4-4m5.618-4.016A11.955 11.955 0 0112 2.944a11.955 11.955 0 01-8.618 3.04A12.02 12.02 0 003 9c0 5.591 3.824 10.29 9 11.622 5.176-1.332 9-6.03 9-11.622 0-1.042-.133-2.052-.382-3.016z" />
        </svg>
      </div>

      <h2 className="text-xl font-semibold text-slate-800 mb-2">Analyzing Evidence</h2>
      <p className="text-guard-600 font-medium mb-8 min-h-[1.5rem] animate-fade-in" key={currentStageIndex}>
        {STAGES[currentStageIndex].label}...
      </p>

      {/* Progress Bar */}
      <div className="w-full bg-slate-100 rounded-full h-2.5 mb-8 overflow-hidden shadow-inner">
        <div 
          className="bg-guard-500 h-2.5 rounded-full transition-all duration-500 ease-out relative" 
          style={{ width: `${progressPercentage}%` }}
        >
          <div className="absolute inset-0 bg-white/20 w-full animate-[progress-bar_2s_ease-in-out_infinite]"></div>
        </div>
      </div>

      {/* Pipeline Stages Checklist */}
      <div className="w-full space-y-3">
        {STAGES.map((stage, index) => {
          const isComplete = index < currentStageIndex;
          const isActive = index === currentStageIndex;
          const isPending = index > currentStageIndex;

          return (
            <div key={stage.id} className={`flex items-center transition-opacity duration-300 ${isPending ? 'opacity-40' : 'opacity-100'}`}>
              <div className="mr-3 flex-shrink-0 w-5 h-5 flex items-center justify-center">
                {isComplete ? (
                  <svg className="w-5 h-5 text-emerald-500" fill="currentColor" viewBox="0 0 20 20">
                    <path fillRule="evenodd" d="M10 18a8 8 0 100-16 8 8 0 000 16zm3.707-9.293a1 1 0 00-1.414-1.414L9 10.586 7.707 9.293a1 1 0 00-1.414 1.414l2 2a1 1 0 001.414 0l4-4z" clipRule="evenodd" />
                  </svg>
                ) : isActive ? (
                  <div className="w-2.5 h-2.5 rounded-full bg-guard-500 animate-pulse"></div>
                ) : (
                  <div className="w-2.5 h-2.5 rounded-full bg-slate-300"></div>
                )}
              </div>
              <span className={`text-sm ${isComplete ? 'text-slate-600 font-medium' : isActive ? 'text-guard-700 font-semibold' : 'text-slate-500'}`}>
                {stage.label}
              </span>
            </div>
          );
        })}
      </div>
    </div>
  );
}
