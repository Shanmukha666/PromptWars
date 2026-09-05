import React from 'react'
import { IconChevronRight } from './Icons'

const STAGE_LABELS = {
  overview: 'Overview',
  profile: 'Patient Profile',
  reports: 'Reports',
  structured: 'Structured Record',
  review: 'Review & Verification',
  timeline: 'Timeline / History',
  processing: 'Processing & Evidence'
}

export default function Breadcrumbs({
  stage,
  activePatient,
  activeDocument,
  onNavigate
}) {
  // Always provide a clean, high-utility trail without visual noise
  const items = []

  // Root
  items.push({
    label: 'MedLens',
    onClick: () => onNavigate('overview')
  })

  // Patient context
  if (activePatient) {
    items.push({
      label: activePatient.name,
      onClick: () => onNavigate('profile')
    })
  }

  // Active Report context if in structured/review/processing
  if ((stage === 'structured' || stage === 'review' || stage === 'processing') && activeDocument) {
    items.push({
      label: activeDocument.title || 'Clinical Report',
      onClick: () => onNavigate('reports')
    })
  }

  // Current stage if not overview
  if (stage !== 'overview') {
    items.push({
      label: STAGE_LABELS[stage] || stage,
      isCurrent: true
    })
  }

  if (items.length <= 1) return null

  return (
    <nav className="breadcrumbs" aria-label="Breadcrumb navigation">
      {items.map((item, idx) => (
        <span key={idx} className="breadcrumb-item">
          {item.isCurrent ? (
            <span className="breadcrumb-current" aria-current="page">{item.label}</span>
          ) : (
            <button
              type="button"
              className="breadcrumb-link"
              onClick={item.onClick}
            >
              {item.label}
            </button>
          )}
          {idx < items.length - 1 && (
            <span className="breadcrumb-sep">
              <IconChevronRight size={13} />
            </span>
          )}
        </span>
      ))}
    </nav>
  )
}
