import React from 'react'
import { IconClose, IconSettings } from './Icons'

export default function SettingsModal({ isOpen, onClose, health, documentsCount, patientsCount }) {
  if (!isOpen) return null

  return (
    <div className="modal-backdrop" onClick={onClose} role="dialog" aria-modal="true">
      <div className="modal-card" onClick={(e) => e.stopPropagation()}>
        <div className="modal-header">
          <div style={{ display: 'flex', alignItems: 'center', gap: '0.5rem' }}>
            <IconSettings size={20} />
            <h3 style={{ margin: 0 }}>System Settings & Workspace Telemetry</h3>
          </div>
          <button className="modal-close-btn" onClick={onClose} aria-label="Close settings modal">
            <IconClose size={20} />
          </button>
        </div>

        <div className="modal-body stack gap-md">
          <div className="card" style={{ background: 'var(--bg-subtle)' }}>
            <h4 style={{ fontSize: '14px', marginBottom: '0.5rem' }}>Processing Engine Configuration</h4>
            <div className="stack gap-sm">
              <div className="meta-row small">
                <span className="muted">Extractor Mode:</span>
                <strong style={{ color: (health?.gemini?.configured || health?.featherless?.configured) ? 'var(--status-success)' : 'var(--status-warning)' }}>
                  {(health?.gemini?.configured || health?.featherless?.configured) ? 'Live Google Gemini LLM' : 'Deterministic Heuristic Fallback'}
                </strong>
              </div>
              <div className="meta-row small">
                <span className="muted">Model:</span>
                <code>{health?.gemini?.model || health?.featherless?.model || 'gemini-1.5-flash'}</code>
              </div>
              <div className="meta-row small">
                <span className="muted">API Base:</span>
                <code>{health?.gemini?.base_url || 'https://generativelanguage.googleapis.com'}</code>
              </div>
              <div className="meta-row small">
                <span className="muted">Clinical Guardrails:</span>
                <strong style={{ color: 'var(--status-success)' }}>Active (Non-diagnostic enforcement)</strong>
              </div>
            </div>
          </div>

          <div className="card" style={{ background: 'var(--bg-subtle)' }}>
            <h4 style={{ fontSize: '14px', marginBottom: '0.5rem' }}>Local Data Store</h4>
            <div className="stack gap-sm">
              <div className="meta-row small">
                <span className="muted">Indexed Patients:</span>
                <strong>{patientsCount} records</strong>
              </div>
              <div className="meta-row small">
                <span className="muted">Processed Reports:</span>
                <strong>{documentsCount} documents</strong>
              </div>
              <div className="meta-row small">
                <span className="muted">Persistence Type:</span>
                <span>SQLite (Sandboxed, Local Storage)</span>
              </div>
              <div className="meta-row small">
                <span className="muted">Reference Range Policy:</span>
                <span style={{ color: 'var(--status-success)', fontWeight: 500 }}>Explicit source ranges only</span>
              </div>
            </div>
          </div>
        </div>

        <div className="modal-footer">
          <button className="secondary-btn" onClick={onClose}>
            Close
          </button>
        </div>
      </div>
    </div>
  )
}
