import React from 'react'

export const WORKFLOW_STAGES = [
  { key: 'overview', step: '1', label: 'Overview', desc: 'Dashboard & Patient Selection' },
  { key: 'profile', step: '2', label: 'Patient Profile', desc: 'Clinical Context & Intake' },
  { key: 'reports', step: '3', label: 'Reports', desc: 'Upload & Process Documents' },
  { key: 'structured', step: '4', label: 'Structured Record', desc: 'Labs, Entities & Safe Summary' },
  { key: 'review', step: '5', label: 'Review & Verification', desc: 'Audit & Edit Uncertain Fields' },
  { key: 'timeline', step: '6', label: 'Timeline / History', desc: 'Trend Analysis & Comparisons' },
  { key: 'processing', step: '7', label: 'Processing & Evidence', desc: 'Transparent Pipeline & Observable Evidence' },
]

export default function Navigation({ currentStage, onSelectStage, activePatient, activeDocument }) {
  return (
    <nav className="workflow-nav" aria-label="Clinical Workflow Steps">
      <div className="workflow-steps" role="list">
        {WORKFLOW_STAGES.map((item, idx) => {
          const isActive = currentStage === item.key
          
          return (
            <button
              key={item.key}
              type="button"
              className={`workflow-step-btn ${isActive ? 'active' : ''}`}
              onClick={() => onSelectStage(item.key)}
              title={item.desc}
              aria-current={isActive ? 'step' : undefined}
              aria-label={`Step ${item.step}: ${item.label} - ${item.desc}`}
            >
              <div className="step-num" aria-hidden="true">{item.step}</div>
              <div className="step-info">
                <div className="step-label">{item.label}</div>
                <div className="step-desc">{item.desc}</div>
              </div>
              {idx < WORKFLOW_STAGES.length - 1 && (
                <div className="step-arrow" aria-hidden="true">→</div>
              )}
            </button>
          )
        })}
      </div>
    </nav>
  )
}
