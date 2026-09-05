import React, { useEffect, useRef } from 'react'
import { IconClose, IconSettings } from './Icons'

export default function SettingsModal({ isOpen, onClose, health, documentsCount, patientsCount }) {
  const dialogRef = useRef(null)
  const previousActiveElementRef = useRef(null)

  useEffect(() => {
    if (!isOpen) return

    previousActiveElementRef.current = document.activeElement

    const timer = setTimeout(() => {
      if (dialogRef.current) {
        const focusable = dialogRef.current.querySelectorAll(
          'button, [href], input, select, textarea, [tabindex]:not([tabindex="-1"])'
        )
        if (focusable.length > 0) {
          focusable[0].focus()
        } else {
          dialogRef.current.focus()
        }
      }
    }, 50)

    function handleKeyDown(e) {
      if (e.key === 'Escape') {
        e.preventDefault()
        onClose()
        return
      }

      if (e.key === 'Tab' && dialogRef.current) {
        const focusables = Array.from(
          dialogRef.current.querySelectorAll(
            'button, [href], input, select, textarea, [tabindex]:not([tabindex="-1"])'
          )
        ).filter(el => !el.disabled && el.offsetParent !== null)

        if (focusables.length === 0) return

        const first = focusables[0]
        const last = focusables[focusables.length - 1]

        if (e.shiftKey && document.activeElement === first) {
          e.preventDefault()
          last.focus()
        } else if (!e.shiftKey && document.activeElement === last) {
          e.preventDefault()
          first.focus()
        }
      }
    }

    window.addEventListener('keydown', handleKeyDown)
    return () => {
      clearTimeout(timer)
      window.removeEventListener('keydown', handleKeyDown)
      if (previousActiveElementRef.current && typeof previousActiveElementRef.current.focus === 'function') {
        previousActiveElementRef.current.focus()
      }
    }
  }, [isOpen, onClose])

  if (!isOpen) return null

  return (
    <div
      className="modal-backdrop"
      onClick={onClose}
      role="presentation"
    >
      <div
        ref={dialogRef}
        className="modal-card"
        onClick={(e) => e.stopPropagation()}
        role="dialog"
        aria-modal="true"
        aria-labelledby="settings-modal-title"
        tabIndex="-1"
      >
        <div className="modal-header">
          <div style={{ display: 'flex', alignItems: 'center', gap: '0.5rem' }}>
            <IconSettings size={20} aria-hidden="true" />
            <h2 id="settings-modal-title" style={{ margin: 0, fontSize: '18px' }}>
              System Settings & Workspace Telemetry
            </h2>
          </div>
          <button
            type="button"
            className="modal-close-btn"
            onClick={onClose}
            aria-label="Close settings modal"
          >
            <IconClose size={20} aria-hidden="true" />
          </button>
        </div>

        <div className="modal-body stack gap-md">
          <div className="card" style={{ background: 'var(--bg-subtle)' }}>
            <h3 style={{ fontSize: '14px', marginBottom: '0.5rem' }}>Processing Engine Configuration</h3>
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
            <h3 style={{ fontSize: '14px', marginBottom: '0.5rem' }}>Local Data Store</h3>
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
          <button
            type="button"
            className="secondary-btn"
            onClick={onClose}
          >
            Close
          </button>
        </div>
      </div>
    </div>
  )
}
