import { useState, useRef } from "react";

interface UploadScreenProps {
  onVerify: (files: File[]) => void;
}

export function UploadScreen({ onVerify }: UploadScreenProps) {
  const [files, setFiles] = useState<File[]>([]);
  const [isDragging, setIsDragging] = useState(false);
  const fileInputRef = useRef<HTMLInputElement>(null);

  const handleDragOver = (e: React.DragEvent) => {
    e.preventDefault();
    setIsDragging(true);
  };

  const handleDragLeave = () => {
    setIsDragging(false);
  };

  const handleDrop = (e: React.DragEvent) => {
    e.preventDefault();
    setIsDragging(false);
    if (e.dataTransfer.files && e.dataTransfer.files.length > 0) {
      const newFiles = Array.from(e.dataTransfer.files);
      setFiles((prev) => [...prev, ...newFiles]);
    }
  };

  const handleFileChange = (e: React.ChangeEvent<HTMLInputElement>) => {
    if (e.target.files && e.target.files.length > 0) {
      const newFiles = Array.from(e.target.files);
      setFiles((prev) => [...prev, ...newFiles]);
    }
  };

  const removeFile = (index: number) => {
    setFiles((prev) => prev.filter((_, i) => i !== index));
  };

  const handleSubmit = () => {
    if (files.length > 0) {
      onVerify(files);
    }
  };

  return (
    <div className="flex flex-col items-center justify-center min-h-[60vh] max-w-2xl mx-auto w-full animate-fade-in">
      <div className="text-center mb-8">
        <h2 className="text-2xl font-semibold text-slate-800 mb-2">Upload Evidence Bundle</h2>
        <p className="text-slate-500 text-sm">Add the applicant's ID, payslips, or bank statements for verification.</p>
      </div>

      <div
        className={`w-full p-10 border-2 border-dashed rounded-xl transition-all duration-200 ease-in-out ${
          isDragging ? "drop-zone-active" : "border-slate-300 bg-white hover:border-guard-400 hover:bg-slate-50"
        }`}
        onDragOver={handleDragOver}
        onDragLeave={handleDragLeave}
        onDrop={handleDrop}
      >
        <div className="flex flex-col items-center text-center">
          <svg className={`w-12 h-12 mb-4 ${isDragging ? "text-guard-500" : "text-slate-400"}`} fill="none" viewBox="0 0 24 24" stroke="currentColor">
            <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={1.5} d="M7 16a4 4 0 01-.88-7.903A5 5 0 1115.9 6L16 6a5 5 0 011 9.9M15 13l-3-3m0 0l-3 3m3-3v12" />
          </svg>
          <p className="text-base font-medium text-slate-700 mb-1">
            Drag and drop files here
          </p>
          <p className="text-sm text-slate-500 mb-4">
            PDF, JPEG, or PNG up to 10MB each
          </p>
          <button
            onClick={() => fileInputRef.current?.click()}
            className="px-4 py-2 bg-white border border-slate-200 rounded-lg text-sm font-medium text-slate-700 hover:bg-slate-50 hover:text-guard-600 transition-colors shadow-sm"
          >
            Browse Files
          </button>
          <input
            type="file"
            multiple
            className="hidden"
            ref={fileInputRef}
            onChange={handleFileChange}
            accept=".pdf,.jpg,.jpeg,.png"
          />
        </div>
      </div>

      {files.length > 0 && (
        <div className="w-full mt-8 animate-slide-up">
          <h3 className="text-sm font-medium text-slate-700 mb-3 uppercase tracking-wider">Attached Files ({files.length})</h3>
          <ul className="space-y-2">
            {files.map((file, index) => (
              <li key={`${file.name}-${index}`} className="flex items-center justify-between p-3 bg-white border border-slate-200 rounded-lg shadow-sm">
                <div className="flex items-center space-x-3 overflow-hidden">
                  <svg className="w-5 h-5 text-guard-500 flex-shrink-0" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                    <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M9 12h6m-6 4h6m2 5H7a2 2 0 01-2-2V5a2 2 0 012-2h5.586a1 1 0 01.707.293l5.414 5.414a1 1 0 01.293.707V19a2 2 0 01-2 2z" />
                  </svg>
                  <span className="text-sm font-medium text-slate-700 truncate">{file.name}</span>
                  <span className="text-xs text-slate-400 flex-shrink-0">{(file.size / 1024 / 1024).toFixed(2)} MB</span>
                </div>
                <button
                  onClick={() => removeFile(index)}
                  className="p-1 text-slate-400 hover:text-red-500 transition-colors rounded-md hover:bg-red-50"
                  aria-label="Remove file"
                >
                  <svg className="w-4 h-4" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                    <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M6 18L18 6M6 6l12 12" />
                  </svg>
                </button>
              </li>
            ))}
          </ul>
          
          <div className="mt-6 flex justify-end">
            <button
              onClick={handleSubmit}
              className="px-6 py-2.5 bg-guard-600 text-white rounded-lg font-medium shadow-md hover:bg-guard-700 focus:ring-4 focus:ring-guard-200 transition-all flex items-center space-x-2"
            >
              <span>Verify Bundle</span>
              <svg className="w-4 h-4" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M14 5l7 7m0 0l-7 7m7-7H3" />
              </svg>
            </button>
          </div>
        </div>
      )}
    </div>
  );
}
