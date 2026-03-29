"use client";

import { useState, useEffect, useCallback } from "react";
import { Eye, EyeOff, X } from "lucide-react";
import { getApiKey, saveApiKey, clearApiKey } from "@/lib/settings";

interface ApiKeyModalProps {
  open: boolean;
  onClose: () => void;
}

export function ApiKeyModal({ open, onClose }: ApiKeyModalProps) {
  const [value, setValue] = useState("");
  const [show, setShow] = useState(false);
  const [saved, setSaved] = useState(false);
  const [prevOpen, setPrevOpen] = useState(false);

  const hasKey = !!getApiKey();

  // Reset state when modal opens (avoids setState in useEffect)
  if (open && !prevOpen) {
    setValue(getApiKey() || "");
    setSaved(false);
    setShow(false);
  }
  if (open !== prevOpen) {
    setPrevOpen(open);
  }

  const handleEscape = useCallback(
    (e: KeyboardEvent) => {
      if (e.key === "Escape") onClose();
    },
    [onClose],
  );

  useEffect(() => {
    if (open) {
      document.addEventListener("keydown", handleEscape);
      return () => document.removeEventListener("keydown", handleEscape);
    }
  }, [open, handleEscape]);

  if (!open) return null;

  const handleSave = () => {
    if (value.trim()) {
      saveApiKey(value);
      setSaved(true);
      setTimeout(onClose, 600);
    }
  };

  const handleClear = () => {
    clearApiKey();
    setValue("");
    setSaved(false);
  };

  return (
    <div
      className="fixed inset-0 z-50 bg-black/60 flex items-center justify-center"
      onClick={(e) => {
        if (e.target === e.currentTarget) onClose();
      }}
      role="dialog"
      aria-modal="true"
      aria-labelledby="apikey-modal-title"
    >
      <div className="bg-surface border border-border rounded-lg p-6 max-w-md w-full mx-4 animate-fade-in">
        {/* Header */}
        <div className="flex items-center justify-between mb-4">
          <h2
            id="apikey-modal-title"
            className="text-sm font-mono font-bold text-white"
          >
            API Key Settings
          </h2>
          <button
            onClick={onClose}
            className="text-muted hover:text-white transition-colors"
            aria-label="Close"
          >
            <X size={16} />
          </button>
        </div>

        {/* Status */}
        <div className="flex items-center gap-2 mb-4 text-xs font-mono">
          <span
            className={`w-2 h-2 rounded-full ${hasKey ? "bg-bullish" : "bg-muted"}`}
          />
          <span className={hasKey ? "text-bullish" : "text-muted"}>
            {hasKey ? "Key saved" : "No key set"}
          </span>
          {saved && (
            <span className="text-bullish ml-auto">Saved!</span>
          )}
        </div>

        {/* Description */}
        <p className="text-xs font-mono text-muted mb-3">
          Paste your Nansen API key to unlock deep dive enrichment. Stored
          locally in your browser — never sent to our server.
        </p>

        {/* Input */}
        <div className="relative mb-4">
          <input
            type={show ? "text" : "password"}
            value={value}
            onChange={(e) => setValue(e.target.value)}
            placeholder="nansen_xxxxxxxxxxxxxxxx"
            className="w-full bg-bg border border-border rounded px-3 py-2 pr-10 text-sm font-mono text-white placeholder:text-muted/50 focus:outline-none focus:border-accent transition-colors"
            autoComplete="off"
            spellCheck={false}
          />
          <button
            onClick={() => setShow(!show)}
            className="absolute right-2 top-1/2 -translate-y-1/2 text-muted hover:text-white transition-colors"
            aria-label={show ? "Hide key" : "Show key"}
            type="button"
          >
            {show ? <EyeOff size={14} /> : <Eye size={14} />}
          </button>
        </div>

        {/* Actions */}
        <div className="flex items-center gap-2">
          <button
            onClick={handleSave}
            disabled={!value.trim()}
            className="px-4 py-1.5 bg-accent text-bg text-sm font-mono font-bold rounded hover:bg-accent/90 transition-colors disabled:opacity-40 disabled:cursor-not-allowed"
          >
            Save
          </button>
          <button
            onClick={handleClear}
            className="px-4 py-1.5 bg-surface-hover text-muted text-sm font-mono rounded hover:text-white transition-colors"
          >
            Clear
          </button>
          <button
            onClick={onClose}
            className="px-4 py-1.5 text-muted text-sm font-mono rounded hover:text-white transition-colors ml-auto"
          >
            Cancel
          </button>
        </div>
      </div>
    </div>
  );
}
