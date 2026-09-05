import React from 'react'
import { IconClose, IconShield } from './Icons'

export default function HelpModal({ isOpen, onClose }) {
  if (!isOpen) return null

  return (
    <div className="modal-backdrop" onClick={onClose} role="dialog" aria-modal="true">
      <div className="modal-card" onClick={(e) => e.stopPropagation()}>
        <div className="modal-header">
          <div style={{ display: 'flex', alignItems: 'center', gap: '0.5rem' }}>
            <IconShield size={20} />
            <h3 style={{ margin: 0 }}>MedLens Clinical Information Principles</h3>
          </div>
          <button className="modal-close-btn" onClick={onClose} aria-label="Close help modal">
            <IconClose size={20} />
          </button>
        </div>

        <div className="modal-body stack gap-md">
          <div className="card" style={{ background: 'var(--bg-subtle)' }}>
            <h4 style={{ fontSize: '14px', marginBottom: '0.35rem', color: 'var(--text-primary)' }}>1. Non-Diagnostic Guarantee</h4>
            <p className="small muted">
              MedLens is an information extraction and synthesis tool, <strong>NOT</strong> a diagnostic system. It does not generate speculative diagnoses, rank potential illnesses, prescribe therapy, or adjust medications.
            </p>
          </div>

          <div className="card" style={{ background: 'var(--bg-subtle)' }}>
            <h4 style={{ fontSize: '14px', marginBottom: '0.35rem', color: 'var(--text-primary)' }}>2. Zero-Hallucination Reference Ranges</h4>
            <p className="small muted">
              Lab results are marked <strong>low, normal, or high ONLY</strong> when explicit reference range bounds are present in the uploaded source report. If absent, the status remains <code>not_assessed</code>.
            </p>
          </div>

          <div className="card" style={{ background: 'var(--bg-subtle)' }}>
            <h4 style={{ fontSize: '14px', marginBottom: '0.35rem', color: 'var(--text-primary)' }}>3. Explicit Provenance Badging</h4>
            <p className="small muted">
              Every data point is strictly labeled with its provenance:
            </p>
            <ul className="small muted" style={{ paddingLeft: '1.25rem', marginTop: '0.35rem', display: 'grid', gap: '0.25rem' }}>
              <li><strong>User-Provided:</strong> Entered during intake (age, symptoms, conditions, medications).</li>
              <li><strong>Source-Extracted:</strong> Extracted directly from report text and tables.</li>
              <li><strong>AI-Generated:</strong> Factual language model summarization with guarded disclaimers.</li>
              <li><strong>User-Verified:</strong> Audited and approved by a clinical reviewer.</li>
            </ul>
          </div>

          <div className="card" style={{ background: 'var(--bg-subtle)' }}>
            <h4 style={{ fontSize: '14px', marginBottom: '0.35rem', color: 'var(--text-primary)' }}>4. Human-in-the-Loop Verification</h4>
            <p className="small muted">
              Use the <strong>Review</strong> tab to inspect source excerpts side-by-side with extracted values, correct OCR discrepancies, and sign off on structured data before longitudinal tracking.
            </p>
          </div>
        </div>

        <div className="modal-footer">
          <button className="primary-btn" onClick={onClose}>
            Got it, return to workspace
          </button>
        </div>
      </div>
    </div>
  )
}
