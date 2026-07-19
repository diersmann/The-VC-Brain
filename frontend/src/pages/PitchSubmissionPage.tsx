import { useState, useRef } from "react";
import { UploadCloud, CheckCircle, FileText, X, ArrowRight, Building2, UserCircle, Mail, Sparkles } from "lucide-react";
import { submitPitch } from "../api/inbound";

export function PitchSubmissionPage() {
  const [file, setFile] = useState<File | null>(null);
  const [isSubmitting, setIsSubmitting] = useState(false);
  const [isSuccess, setIsSuccess] = useState(false);
  const fileInputRef = useRef<HTMLInputElement>(null);

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!file) return;
    
    setIsSubmitting(true);
    
    const formElement = e.currentTarget as HTMLFormElement;
    const formData = new FormData(formElement);
    formData.append("file", file);
    
    try {
      await submitPitch(formData);
      setIsSuccess(true);
    } catch (error) {
      console.error("Failed to submit pitch", error);
      alert("There was an error submitting your pitch. Please try again.");
    } finally {
      setIsSubmitting(false);
    }
  };

  const handleDragOver = (e: React.DragEvent) => {
    e.preventDefault();
  };

  const handleDrop = (e: React.DragEvent) => {
    e.preventDefault();
    if (e.dataTransfer.files && e.dataTransfer.files.length > 0) {
      setFile(e.dataTransfer.files[0]);
    }
  };

  if (isSuccess) {
    return (
      <div className="min-h-screen bg-neutral-950 text-white flex items-center justify-center p-6 font-sans relative overflow-hidden">
        {/* Decorative background blobs */}
        <div className="absolute top-1/4 left-1/4 w-96 h-96 bg-purple-600/20 rounded-full blur-[120px]" />
        <div className="absolute bottom-1/4 right-1/4 w-[500px] h-[500px] bg-blue-600/20 rounded-full blur-[150px]" />
        
        <div className="relative z-10 max-w-md w-full bg-neutral-900/50 backdrop-blur-xl border border-white/10 rounded-3xl p-10 text-center shadow-2xl transition-all duration-500 ease-out transform translate-y-0 opacity-100">
          <div className="mx-auto w-20 h-20 bg-green-500/20 rounded-full flex items-center justify-center mb-6">
            <CheckCircle className="w-10 h-10 text-green-400" />
          </div>
          <h2 className="text-3xl font-bold mb-3 tracking-tight bg-gradient-to-r from-white to-neutral-400 bg-clip-text text-transparent">Pitch Received</h2>
          <p className="text-neutral-400 mb-8 leading-relaxed">
            Thank you for sharing your vision with us. Our investment team will review your deck and get back to you shortly.
          </p>
          <button 
            onClick={() => setIsSuccess(false)}
            className="w-full py-3.5 bg-white/10 hover:bg-white/20 text-white rounded-xl font-medium transition-colors border border-white/5 cursor-pointer"
          >
            Submit Another
          </button>
        </div>
      </div>
    );
  }

  return (
    <div className="min-h-screen bg-neutral-950 text-neutral-100 flex items-center justify-center p-6 sm:p-12 font-sans relative overflow-hidden selection:bg-purple-500/30">
      {/* Dynamic Background */}
      <div className="absolute inset-0 z-0 overflow-hidden pointer-events-none">
        <div className="absolute top-[-10%] left-[-10%] w-[40%] h-[40%] bg-purple-600/20 rounded-full blur-[120px] mix-blend-screen" />
        <div className="absolute bottom-[-10%] right-[-10%] w-[50%] h-[50%] bg-blue-600/20 rounded-full blur-[150px] mix-blend-screen" />
        <div className="absolute top-[40%] left-[60%] w-[30%] h-[30%] bg-emerald-600/10 rounded-full blur-[100px] mix-blend-screen" />
      </div>

      <div className="relative z-10 max-w-5xl w-full grid lg:grid-cols-2 gap-12 lg:gap-24 items-center">
        {/* Left Side: Copy & Branding */}
        <div className="space-y-8">
          <div className="inline-flex items-center gap-2 px-3 py-1.5 rounded-full bg-white/5 border border-white/10 text-sm font-medium text-purple-300">
            <Sparkles className="w-4 h-4" />
            <span>Fund Application</span>
          </div>
          
          <h1 className="text-5xl lg:text-6xl font-extrabold tracking-tight leading-[1.1] text-transparent bg-clip-text bg-gradient-to-br from-white via-neutral-200 to-neutral-500">
            Ready to build the future?
          </h1>
          
          <p className="text-lg text-neutral-400 leading-relaxed max-w-xl">
            Submit your pitch deck to be considered for our next cohort. We analyze your team, product, market, and traction to make swift, evidence-backed decisions.
          </p>
          
          <div className="grid sm:grid-cols-2 gap-6 pt-4">
            <div className="space-y-2">
              <h3 className="text-white font-semibold flex items-center gap-2">
                <div className="w-1.5 h-1.5 rounded-full bg-purple-500" /> Fast Response
              </h3>
              <p className="text-sm text-neutral-500">Expect a reply within 24 hours.</p>
            </div>
            <div className="space-y-2">
              <h3 className="text-white font-semibold flex items-center gap-2">
                <div className="w-1.5 h-1.5 rounded-full bg-blue-500" /> Deep Analysis
              </h3>
              <p className="text-sm text-neutral-500">AI-powered initial screening.</p>
            </div>
          </div>
        </div>

        {/* Right Side: Form */}
        <div className="bg-neutral-900/60 backdrop-blur-2xl border border-white/10 rounded-3xl p-8 shadow-[0_0_80px_rgba(0,0,0,0.5)] relative">
          {/* Subtle inner glow */}
          <div className="absolute inset-0 rounded-3xl border border-white/5 pointer-events-none mix-blend-overlay" />
          
          <form onSubmit={handleSubmit} className="space-y-6 relative z-10">
            <div className="space-y-4">
              {/* Founder Name */}
              <div className="relative group">
                <div className="absolute inset-y-0 left-0 pl-4 flex items-center pointer-events-none text-neutral-500 group-focus-within:text-purple-400 transition-colors">
                  <UserCircle className="w-5 h-5" />
                </div>
                <input 
                  type="text" 
                  name="founder_name"
                  required
                  placeholder="Founder Name" 
                  className="w-full bg-neutral-950/50 border border-white/10 rounded-xl py-3.5 pl-12 pr-4 text-white placeholder:text-neutral-600 focus:outline-none focus:ring-2 focus:ring-purple-500/50 focus:border-purple-500/50 transition-all"
                />
              </div>

              {/* Email */}
              <div className="relative group">
                <div className="absolute inset-y-0 left-0 pl-4 flex items-center pointer-events-none text-neutral-500 group-focus-within:text-purple-400 transition-colors">
                  <Mail className="w-5 h-5" />
                </div>
                <input 
                  type="email" 
                  name="founder_email"
                  required
                  placeholder="Email Address" 
                  className="w-full bg-neutral-950/50 border border-white/10 rounded-xl py-3.5 pl-12 pr-4 text-white placeholder:text-neutral-600 focus:outline-none focus:ring-2 focus:ring-purple-500/50 focus:border-purple-500/50 transition-all"
                />
              </div>

              {/* Company */}
              <div className="relative group">
                <div className="absolute inset-y-0 left-0 pl-4 flex items-center pointer-events-none text-neutral-500 group-focus-within:text-purple-400 transition-colors">
                  <Building2 className="w-5 h-5" />
                </div>
                <input 
                  type="text" 
                  name="company_name"
                  required
                  placeholder="Company Name" 
                  className="w-full bg-neutral-950/50 border border-white/10 rounded-xl py-3.5 pl-12 pr-4 text-white placeholder:text-neutral-600 focus:outline-none focus:ring-2 focus:ring-purple-500/50 focus:border-purple-500/50 transition-all"
                />
              </div>
            </div>

            {/* File Upload */}
            <div 
              onDragOver={handleDragOver}
              onDrop={handleDrop}
              onClick={() => fileInputRef.current?.click()}
              className={`relative overflow-hidden group cursor-pointer border-2 border-dashed rounded-2xl transition-all duration-300 ${
                file ? 'border-purple-500/50 bg-purple-500/5' : 'border-white/10 bg-neutral-950/50 hover:border-white/30 hover:bg-neutral-950/80'
              }`}
            >
              <input 
                type="file" 
                ref={fileInputRef} 
                accept=".pdf,.ppt,.pptx" 
                className="hidden" 
                onChange={(e) => setFile(e.target.files?.[0] ?? null)}
              />
              
              <div className="p-8 text-center flex flex-col items-center justify-center min-h-[160px]">
                {file ? (
                  <div className="flex flex-col items-center gap-3 relative z-10 w-full">
                    <div className="w-12 h-12 bg-purple-500/20 text-purple-400 rounded-full flex items-center justify-center">
                      <FileText className="w-6 h-6" />
                    </div>
                    <div className="max-w-[200px] w-full">
                      <p className="text-white font-medium truncate">{file.name}</p>
                      <p className="text-xs text-neutral-500 mt-1">{(file.size / (1024 * 1024)).toFixed(2)} MB</p>
                    </div>
                    <button 
                      type="button" 
                      onClick={(e) => { e.stopPropagation(); setFile(null); }}
                      className="absolute right-2 top-1/2 -translate-y-1/2 p-2 hover:bg-white/10 rounded-full transition-colors text-neutral-400 hover:text-white cursor-pointer"
                    >
                      <X className="w-4 h-4" />
                    </button>
                  </div>
                ) : (
                  <div className="flex flex-col items-center gap-4 relative z-10">
                    <div className="w-14 h-14 bg-white/5 text-neutral-400 group-hover:text-purple-400 group-hover:scale-110 rounded-full flex items-center justify-center transition-all duration-300">
                      <UploadCloud className="w-7 h-7" />
                    </div>
                    <div>
                      <p className="text-white font-medium">Upload Pitch Deck</p>
                      <p className="text-xs text-neutral-500 mt-1">Drag & drop or click to browse (PDF, PPT)</p>
                    </div>
                  </div>
                )}
              </div>
            </div>

            {/* Submit Button */}
            <button 
              type="submit" 
              disabled={isSubmitting || !file}
              className="w-full relative group overflow-hidden rounded-xl bg-white text-black font-semibold py-4 transition-all hover:bg-neutral-200 disabled:opacity-50 disabled:cursor-not-allowed cursor-pointer"
            >
              <div className="absolute inset-0 bg-gradient-to-r from-purple-500/20 to-blue-500/20 opacity-0 group-hover:opacity-100 transition-opacity" />
              <div className="flex items-center justify-center gap-2 relative z-10">
                {isSubmitting ? (
                  <div className="w-5 h-5 border-2 border-black/30 border-t-black rounded-full animate-spin" />
                ) : (
                  <>
                    <span>Submit Pitch</span>
                    <ArrowRight className="w-4 h-4 group-hover:translate-x-1 transition-transform" />
                  </>
                )}
              </div>
            </button>
          </form>
        </div>
      </div>
    </div>
  );
}
