import React from 'react'
import ProvenanceBadge from './ProvenanceBadge'
import { IconShield, IconHelp, IconMenu } from './Icons'

export default function TopBar({
  patients = [],
  activePatient,
  onSelectPatient,
  onNewPatient,
  onOpenHelp,
  onToggleMobileSidebar
}) {
  return (
    <header className="top-bar">
      <div className="top-bar-left">
        <button
          className="mobile-menu-btn"
          onClick={onToggleMobileSidebar}
          aria-label="Open Navigation Menu"
        >
          <IconMenu size={20} />
        </button>

        {/* Patient Selector */}
        <div className="patient-selector-wrap">
          <label htmlFor="patient-select" className="top-bar-label">Patient</label>
          <div className="patient-select-controls">
            <select
              id="patient-select"
              value={activePatient?.patient_id || ''}
              onChange={(e) => {
                if (e.target.value === '__new__') {
                  onNewPatient()
                } else if (e.target.value) {
                  onSelectPatient(e.target.value)
                }
              }}
              className="patient-select"
            >
              <option value="" disabled>Select patient...</option>
              {patients.map(p => (
                <option key={p.patient_id} value={p.patient_id}>
                  {p.name} {p.age ? `(${p.age}y` : ''}{p.sex ? `, ${p.sex})` : p.age ? ')' : ''}
                </option>
              ))}
              <option value="__new__">+ New Patient Intake...</option>
            </select>
            <button
              onClick={onNewPatient}
              className="secondary-btn btn-sm"
              title="Intake New Patient"
            >
              + New
            </button>
          </div>
        </div>

        {/* Demographic Context Pill */}
        {activePatient ? (
          <div className="demographic-context-pill">
            <div className="demo-item">
              <span className="demo-label">Age/Sex:</span>
              <span className="demo-val">{activePatient.age || '—'} / {activePatient.sex || '—'}</span>
            </div>
            {activePatient.conditions?.length > 0 && (
              <div className="demo-item hide-mobile">
                <span className="demo-label">Conditions:</span>
                <span className="demo-val">{activePatient.conditions.length} documented</span>
              </div>
            )}
            {activePatient.allergies?.length > 0 && (
              <div className="demo-item hide-mobile">
                <span className="demo-label">Allergies:</span>
                <span className="demo-val" style={{ color: 'var(--status-warning)' }}>
                  {activePatient.allergies.join(', ')}
                </span>
              </div>
            )}
            <ProvenanceBadge type="user_provided" size="small" />
          </div>
        ) : (
          <div className="demographic-context-pill inactive">
            <span className="small muted">No patient context active</span>
          </div>
        )}
      </div>

      <div className="top-bar-right">
        {/* Privacy & Guardrail status */}
        <div className="privacy-badge" title="MedLens processes clinical records locally with strict provenance attribution and no diagnostic overreach.">
          <IconShield size={15} />
          <span className="privacy-text">Private & Provenance-Grounded</span>
        </div>

        {/* Help Action */}
        <button
          className="help-btn"
          onClick={onOpenHelp}
          title="Clinical Safety & Workflow Help"
          aria-label="Help and Clinical Safety Principles"
        >
          <IconHelp size={16} />
          <span className="hide-mobile">Help</span>
        </button>
      </div>
    </header>
  )
}
