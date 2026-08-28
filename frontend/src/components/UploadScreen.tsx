import { useRef, useState } from "react";
import { stagger } from "../motion";

interface UploadScreenProps {
  onVerify: (files: File[]) => void;
}

const ACCEPT = ".pdf,.jpg,.jpeg,.png";

function formatSize(bytes: number): string {
  if (bytes < 1024) return `${bytes} B`;
  if (bytes < 1024 * 1024) return `${(bytes / 1024).toFixed(0)} KB`;
  return `${(bytes / 1024 / 1024).toFixed(1)} MB`;
}

function FileGlyph({ name }: { name: string }) {
  const isPdf = name.toLowerCase().endsWith(".pdf");
  return (
    <span
      className={`flex h-9 w-9 flex-shrink-0 items-center justify-center rounded-lg ${
        isPdf ? "bg-rose-50 text-rose-600" : "bg-guard-50 text-guard-600"
      }`}
      aria-hidden="true"
    >
      {isPdf ? (
        <svg width="18" height="18" fill="none" viewBox="0 0 24 24" stroke="currentColor">
          <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={1.8} d="M9 12h6m-6 4h6m2 5H7a2 2 0 01-2-2V5a2 2 0 012-2h5.586a1 1 0 01.707.293l5.414 5.414a1 1 0 01.293.707V19a2 2 0 01-2 2z" />
        </svg>
      ) : (
        <svg width="18" height="18" fill="none" viewBox="0 0 24 24" stroke="currentColor">
          <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={1.8} d="M2.25 15.75l5.159-5.159a2.25 2.25 0 013.182 0l5.159 5.159m-1.5-1.5l1.409-1.409a2.25 2.25 0 013.182 0l2.909 2.909M18 6h.008v.008H18V6zm2.25 12H3.75A1.5 1.5 0 012.25 16.5v-9A1.5 1.5 0 013.75 6h16.5A1.5 1.5 0 0121.75 7.5v9a1.5 1.5 0 01-1.5 1.5z" />
        </svg>
      )}
    </span>
  );
}

export function UploadScreen({ onVerify }: UploadScreenProps) {
  const [files, setFiles] = useState<File[]>([]);
  const [isDragging, setIsDragging] = useState(false);
  const [removing, setRemoving] = useState<string | null>(null);
  const inputRef = useRef<HTMLInputElement>(null);
  const dragDepth = useRef(0);

  const addFiles = (incoming: FileList | null) => {
    if (!incoming || incoming.length === 0) return;
    setFiles((prev) => [...prev, ...Array.from(incoming)]);
  };

  /* Depth counter stops the highlight flickering as the pointer crosses
     child elements inside the drop zone. */
  const onDragEnter = (e: React.DragEvent) => {
    e.preventDefault();
    dragDepth.current += 1;
    setIsDragging(true);
  };
  const onDragLeave = (e: React.DragEvent) => {
    e.preventDefault();
    dragDepth.current -= 1;
    if (dragDepth.current <= 0) {
      dragDepth.current = 0;
      setIsDragging(false);
    }
  };
  const onDrop = (e: React.DragEvent) => {
    e.preventDefault();
    dragDepth.current = 0;
    setIsDragging(false);
    addFiles(e.dataTransfer.files);
  };

  /* Removal plays a short exit before the item leaves the list, so cards do
     not simply vanish. */
  const keyFor = (f: File, i: number) => `${f.name}-${f.size}-${f.lastModified}-${i}`;
  const removeFile = (key: string, index: number) => {
    setRemoving(key);
    window.setTimeout(() => {
      setFiles((prev) => prev.filter((_, i) => i !== index));
      setRemoving(null);
    }, 140);
  };

  const totalBytes = files.reduce((sum, f) => sum + f.size, 0);
  const ready = files.length > 0;

  return (
    <div className="mx-auto w-full max-w-3xl py-6 sm:py-10">
      {/* ── Hero ─────────────────────────────────────────────────────── */}
      <header className="eg-reveal text-center">
        <span className="inline-flex items-center gap-1.5 rounded-full border border-guard-100 bg-guard-50 px-3 py-1 text-xs font-medium text-guard-700">
          <span className="h-1.5 w-1.5 rounded-full bg-guard-500" aria-hidden="true" />
          Evidence verification
        </span>
        <h2 className="mt-4 text-2xl font-semibold tracking-tight text-slate-900 sm:text-3xl">
          Upload an evidence bundle
        </h2>
        <p className="mx-auto mt-3 max-w-lg text-sm leading-relaxed text-slate-600">
          Add every document for one applicant together — identity, payslips, statements.
          Cross-document checks only run when the documents are verified as a set.
        </p>
      </header>

      {/* ── Drop zone ────────────────────────────────────────────────── */}
      <div
        className={`eg-reveal mt-8 rounded-2xl border-2 border-dashed p-8 text-center transition-colors sm:p-12 ${
          isDragging
            ? "drop-zone-active"
            : "border-slate-300 bg-white hover:border-guard-400 hover:bg-slate-50/70"
        }`}
        style={stagger(1)}
        onDragEnter={onDragEnter}
        onDragOver={(e) => e.preventDefault()}
        onDragLeave={onDragLeave}
        onDrop={onDrop}
      >
        <div
          className={`mx-auto mb-4 flex h-14 w-14 items-center justify-center rounded-2xl transition-colors ${
            isDragging ? "bg-guard-100 text-guard-700" : "bg-slate-100 text-slate-500"
          }`}
          aria-hidden="true"
        >
          <svg className="h-7 w-7" fill="none" viewBox="0 0 24 24" stroke="currentColor">
            <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={1.5} d="M12 16.5V9.75m0 0l3 3m-3-3l-3 3M6.75 19.5a4.5 4.5 0 01-1.41-8.775 5.25 5.25 0 0110.233-2.33 3 3 0 013.758 3.848A3.752 3.752 0 0118 19.5H6.75z" />
          </svg>
        </div>

        <p className="text-base font-medium text-slate-800">
          {isDragging ? "Release to attach" : "Drag and drop documents here"}
        </p>
        <p className="mt-1 text-sm text-slate-500">PDF, JPEG or PNG · up to 10 files</p>

        <button
          type="button"
          onClick={() => inputRef.current?.click()}
          className="eg-press mt-5 inline-flex min-h-[44px] items-center gap-2 rounded-lg border border-slate-300 bg-white px-4 py-2.5 text-sm font-medium text-slate-700 shadow-sm hover:border-guard-400 hover:text-guard-700"
        >
          <svg className="h-4 w-4" fill="none" viewBox="0 0 24 24" stroke="currentColor" aria-hidden="true">
            <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M12 4.5v15m7.5-7.5h-15" />
          </svg>
          Browse files
        </button>

        <input
          ref={inputRef}
          type="file"
          multiple
          accept={ACCEPT}
          className="sr-only"
          onChange={(e) => {
            addFiles(e.target.files);
            e.target.value = ""; // allow re-selecting the same file
          }}
        />
      </div>

      {/* ── Attached files ───────────────────────────────────────────── */}
      {ready ? (
        <section className="mt-8" aria-labelledby="attached-heading">
          <div className="mb-3 flex items-baseline justify-between">
            <h3 id="attached-heading" className="text-sm font-semibold text-slate-800">
              Attached documents
              <span className="ml-2 rounded-full bg-slate-100 px-2 py-0.5 text-xs font-medium text-slate-600">
                {files.length}
              </span>
            </h3>
            <span className="tabular text-xs text-slate-500">{formatSize(totalBytes)} total</span>
          </div>

          <ul className="space-y-2">
            {files.map((file, index) => {
              const key = keyFor(file, index);
              return (
                <li
                  key={key}
                  style={stagger(index)}
                  className={`eg-card flex items-center gap-3 p-3 ${
                    removing === key ? "eg-exit" : "eg-slide-in"
                  }`}
                >
                  <FileGlyph name={file.name} />
                  <div className="min-w-0 flex-1">
                    <p className="truncate text-sm font-medium text-slate-800" title={file.name}>
                      {file.name}
                    </p>
                    <p className="tabular text-xs text-slate-500">{formatSize(file.size)}</p>
                  </div>
                  <button
                    type="button"
                    onClick={() => removeFile(key, index)}
                    className="eg-press flex h-11 w-11 flex-shrink-0 items-center justify-center rounded-lg text-slate-400 hover:bg-rose-50 hover:text-rose-600"
                    aria-label={`Remove ${file.name}`}
                  >
                    <svg className="h-4 w-4" fill="none" viewBox="0 0 24 24" stroke="currentColor" aria-hidden="true">
                      <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M6 18L18 6M6 6l12 12" />
                    </svg>
                  </button>
                </li>
              );
            })}
          </ul>

          <div className="mt-6 flex flex-col-reverse gap-3 sm:flex-row sm:items-center sm:justify-between">
            <button
              type="button"
              onClick={() => setFiles([])}
              className="eg-press min-h-[44px] rounded-lg px-3 text-sm font-medium text-slate-500 hover:text-slate-800"
            >
              Clear all
            </button>
            <button
              type="button"
              onClick={() => onVerify(files)}
              className="eg-press inline-flex min-h-[44px] items-center justify-center gap-2 rounded-lg bg-guard-600 px-6 py-2.5 text-sm font-semibold text-white shadow-sm hover:bg-guard-700"
            >
              Verify bundle
              <svg className="h-4 w-4" fill="none" viewBox="0 0 24 24" stroke="currentColor" aria-hidden="true">
                <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M13.5 4.5L21 12m0 0l-7.5 7.5M21 12H3" />
              </svg>
            </button>
          </div>
        </section>
      ) : (
        /* Empty state — tells the reviewer what the product will do next. */
        <div className="eg-reveal mt-8 rounded-xl border border-slate-200 bg-white/60 p-5" style={stagger(2)}>
          <p className="text-xs font-semibold uppercase tracking-wider text-slate-500">
            What happens on verify
          </p>
          <p className="mt-2 text-sm leading-relaxed text-slate-600">
            Each document is read with local OCR, checked for manipulation signals, then
            compared against the others in the bundle. Nothing is sent to a third party.
          </p>
        </div>
      )}
    </div>
  );
}
