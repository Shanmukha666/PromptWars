import React from 'react'

export const WORKFLOW_STAGES = [
  { key: 'overview', step: '1', label: 'Overview', desc: 'Dashboard & Patient Selection' },
  { key: 'profile', step: '2', label: 'Patient Profile', desc: 'Clinical Context & Intake' },
  { key: 'reports', step: '3', label: 'Reports', desc: 'Upload & Process Documents' },
  { key: 'structured', step: '4', label: 'Structured Record', desc: 'Labs, Entities & Safe Summary' },
  { key: 'review', step: '5', label: 'Review & Verification', desc: 'Audit & Edit Uncertain Fields' },
  { key: 'timeline', step: '6', label: 'Timeline / History', desc: 'Trend Analysis & Comparisons' },
]

export default function Navigation({ currentStage, onSelectStage, activePatient, activeDocument }) {
  return (
    <nav className="workflow-nav" aria-label="Clinical Workflow Navigation">
      <div className="workflow-steps">
        {WORKFLOW_STAGES.map((item, idx) => {
          const isActive = currentStage === item.key
          const isEnabled = item.key === 'overview' || activePatient || (item.key === 'profile')
          
          return (
            <button
              key={item.key}
              className={`workflow-step-btn ${isActive ? 'active' : ''}`}
              onClick={() => onSelectStage(item.key)}
              title={item.desc}
            >
              <div className="step-num">{item.step}</div>
              <div className="step-info">
                <div className="step-label">{item.label}</div>
                <div className="step-desc">{item.desc}</div>
              </div>
              {idx < WORKFLOW_STAGES.length - 1 && <div className="step-arrow">→</div>}
            </button>
          )
        })}
      </div>
    </nav>
  )
}