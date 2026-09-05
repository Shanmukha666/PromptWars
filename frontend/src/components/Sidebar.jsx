import React from 'react'
import {
  IconOverview,
  IconPatient,
  IconReports,
  IconStructured,
  IconReview,
  IconTimeline,
  IconProcessing,
  IconSettings,
  IconClose
} from './Icons'

export const NAV_ITEMS = [
  { key: 'overview', label: 'Overview', icon: IconOverview },
  { key: 'profile', label: 'Patient', icon: IconPatient },
  { key: 'reports', label: 'Reports', icon: IconReports },
  { key: 'structured', label: 'Structured Record', icon: IconStructured },
  { key: 'review', label: 'Review', icon: IconReview },
  { key: 'timeline', label: 'Timeline', icon: IconTimeline },
  { key: 'processing', label: 'Processing & Evidence', icon: IconProcessing },
]

export default function Sidebar({
  currentStage,
  onSelectStage,
  onOpenSettings,
  isOpenMobile,
  onCloseMobile,
  reportsCount = 0
}) {
  return (
    <>
      {/* Mobile overlay backdrop */}
      {isOpenMobile && (
        <div
          className="sidebar-mobile-overlay"
          onClick={onCloseMobile}
          aria-label="Close navigation sidebar overlay"
          role="presentation"
        />
      )}

      <aside
        className={`sidebar ${isOpenMobile ? 'mobile-open' : ''}`}
        aria-label="Main Navigation Sidebar"
      >
        {/* Brand Header */}
        <div className="sidebar-brand-wrap">
          <div className="sidebar-brand">
            <div className="brand-mark" aria-hidden="true">ML</div>
            <div className="brand-text">
              <span className="brand-name">MedLens</span>
              <span className="brand-sub">Clinical Intelligence</span>
            </div>
          </div>
          {isOpenMobile && (
            <button
              type="button"
              className="sidebar-close-mobile-btn"
              onClick={onCloseMobile}
              aria-label="Close navigation sidebar"
            >
              <IconClose size={18} aria-hidden="true" />
            </button>
          )}
        </div>

        {/* Primary Navigation Items */}
        <nav className="sidebar-nav" aria-label="Workflow Stages">
          <div className="sidebar-section-title" id="sidebar-workflow-heading">Workflow</div>
          <div className="sidebar-items" role="list" aria-labelledby="sidebar-workflow-heading">
            {NAV_ITEMS.map((item) => {
              const Icon = item.icon
              const isActive = currentStage === item.key

              return (
                <button
                  key={item.key}
                  type="button"
                  className={`sidebar-nav-btn ${isActive ? 'active' : ''}`}
                  onClick={() => {
                    onSelectStage(item.key)
                    if (isOpenMobile) onCloseMobile()
                  }}
                  aria-current={isActive ? 'page' : undefined}
                >
                  <Icon size={18} aria-hidden="true" />
                  <span className="sidebar-btn-label">{item.label}</span>
                  {item.key === 'reports' && reportsCount > 0 && (
                    <span
                      className="sidebar-badge"
                      aria-label={`${reportsCount} reports available`}
                    >
                      {reportsCount}
                    </span>
                  )}
                </button>
              )
            })}
          </div>
        </nav>

        {/* Bottom Settings Link */}
        <div className="sidebar-footer">
          <button
            type="button"
            className="sidebar-footer-btn"
            onClick={onOpenSettings}
            aria-label="Open System Settings & Telemetry dialog"
          >
            <IconSettings size={18} aria-hidden="true" />
            <span>Settings & Telemetry</span>
          </button>
        </div>
      </aside>
    </>
  )
}
