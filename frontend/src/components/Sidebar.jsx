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
          aria-label="Close navigation sidebar"
        />
      )}

      <aside className={`sidebar ${isOpenMobile ? 'mobile-open' : ''}`}>
        {/* Brand Header */}
        <div className="sidebar-brand-wrap">
          <div className="sidebar-brand">
            <div className="brand-mark">ML</div>
            <div className="brand-text">
              <span className="brand-name">MedLens</span>
              <span className="brand-sub">Clinical Intelligence</span>
            </div>
          </div>
          {isOpenMobile && (
            <button className="sidebar-close-mobile-btn" onClick={onCloseMobile}>
              <IconClose size={18} />
            </button>
          )}
        </div>

        {/* Primary Navigation Items */}
        <nav className="sidebar-nav" aria-label="Main Navigation">
          <div className="sidebar-section-title">Workflow</div>
          <ul className="sidebar-nav-list">
            {NAV_ITEMS.map((item) => {
              const Icon = item.icon
              const isActive = currentStage === item.key
              return (
                <li key={item.key}>
                  <button
                    type="button"
                    className={`sidebar-nav-item ${isActive ? 'active' : ''}`}
                    onClick={() => {
                      onSelectStage(item.key)
                      if (onCloseMobile) onCloseMobile()
                    }}
                    aria-current={isActive ? 'page' : undefined}
                  >
                    <span className="sidebar-nav-icon">
                      <Icon size={18} />
                    </span>
                    <span className="sidebar-nav-label">{item.label}</span>
                    {item.key === 'reports' && reportsCount > 0 && (
                      <span className="sidebar-nav-count">{reportsCount}</span>
                    )}
                  </button>
                </li>
              )
            })}
          </ul>
        </nav>

        {/* Bottom actions / Settings */}
        <div className="sidebar-footer">
          <button
            type="button"
            className="sidebar-footer-btn"
            onClick={() => {
              onOpenSettings()
              if (onCloseMobile) onCloseMobile()
            }}
          >
            <span className="sidebar-nav-icon">
              <IconSettings size={18} />
            </span>
            <span className="sidebar-nav-label">Settings</span>
          </button>
        </div>
      </aside>
    </>
  )
}
