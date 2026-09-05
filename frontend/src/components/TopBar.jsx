import React from 'react'
import ProvenanceBadge from './ProvenanceBadge'
import { IconShield, IconHelp, IconMenu } from './Icons'

export default function TopBar({
  patients = [],
  activePatient,
  onSelectPatient,
  onNewPatient,
  onOpenHelp,
  onToggleMobileSidebar,
  isOpenMobile = false
}) {
  return (
    <header className="top-bar" role="banner">
      <div className="top-bar-left">
        <button
          className="mobile-menu-btn"
          onClick={onToggleMobileSidebar}
          aria-label="Open Navigation Menu"
          aria-expanded={isOpenMobile}
        >
          <IconMenu size={20} aria-hidden="true" />
        </button>

        {/* Patient Selector */}
        <div className="patient-selector-wrap">
          <label htmlFor="header-patient-select" className="top-bar-label">
            Patient:
          </label>
          <div className="patient-select-controls">
            <select
              id="header-patient-select"
              value={activePatient?.patient_id || ''}
              onChange={(e) => {
                if (e.target.value === '__new__') {
                  onNewPatient()
                } else if (e.target.value) {
                  onSelectPatient(e.target.value)
                }
              }}
              className="patient-select"
              aria-label="Select active patient record"
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
              type="button"
              onClick={onNewPatient}
              className="secondary-btn btn-sm"
              title="Intake New Patient"
              aria-label="Intake New Patient Profile"
            >
              + New
            </button>
          </div>
        </div>

        {/* Demographic Context Pill */}
        {activePatient ? (
          <div className="demographic-context-pill" aria-label={`Patient demographic details: ${activePatient.name}`}>
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
        <div
          className="privacy-badge"
          title="MedLens processes clinical records locally with strict provenance attribution and no diagnostic overreach."
          role="status"
          aria-label="Status: Private and Provenance Grounded"
        >
          <IconShield size={15} aria-hidden="true" />
          <span className="privacy-text">Private & Provenance-Grounded</span>
        </div>

        {/* Help Action */}
        <button
          type="button"
          className="help-btn"
          onClick={onOpenHelp}
          title="Clinical Safety & Workflow Help"
          aria-label="Open clinical safety guidance and help documentation"
        >
          <IconHelp size={16} aria-hidden="true" />
          <span className="hide-mobile">Help</span>
        </button>
      </div>
    </header>
  )
}
