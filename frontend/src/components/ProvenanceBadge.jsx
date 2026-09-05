import React, { useState, useRef, useEffect } from 'react'

/**
 * Supported provenance types:
 * 1. user_provided: "User provided" (Source: patient intake)
 * 2. source_extracted / extracted: "Extracted" (Source: report name, page X)
 * 3. ai_generated: "AI generated" (Generated from available structured information)
 * 4. user_verified / verified: "Verified" (Edited and confirmed by user)
 */

export const PROVENANCE_CONFIG = {
  user_provided: {
    key: 'user_provided',
    label: 'User provided',
    defaultSource: 'patient intake',
    defaultDescription: 'Supplied directly by patient or clinician during intake.',
    dotColor: '#7C3AED',
    textColor: '#6D28D9',
    bgColor: '#FAF5FF',
    borderColor: '#E9D5FF'
  },
  source_extracted: {
    key: 'source_extracted',
    label: 'Extracted',
    defaultSource: 'report document',
    defaultDescription: 'Extracted directly from uploaded laboratory or clinical report.',
    dotColor: '#16A34A',
    textColor: '#15803D',
    bgColor: '#F0FDF4',
    borderColor: '#BBF7D0'
  },
  extracted: {
    key: 'source_extracted',
    label: 'Extracted',
    defaultSource: 'report document',
    defaultDescription: 'Extracted directly from uploaded laboratory or clinical report.',
    dotColor: '#16A34A',
    textColor: '#15803D',
    bgColor: '#F0FDF4',
    borderColor: '#BBF7D0'
  },
  ai_generated: {
    key: 'ai_generated',
    label: 'AI generated',
    defaultSource: 'available structured information',
    defaultDescription: 'Generated from available structured information. Never presented as original source text.',
    dotColor: '#0284C7',
    textColor: '#0369A1',
    bgColor: '#F0F9FF',
    borderColor: '#BAE6FD'
  },
  user_verified: {
    key: 'user_verified',
    label: 'Verified',
    defaultSource: 'clinician audit',
    defaultDescription: 'Edited and confirmed by user.',
    dotColor: '#D97706',
    textColor: '#B45309',
    bgColor: '#FFFBEB',
    borderColor: '#FDE68A'
  },
  verified: {
    key: 'user_verified',
    label: 'Verified',
    defaultSource: 'clinician audit',
    defaultDescription: 'Edited and confirmed by user.',
    dotColor: '#D97706',
    textColor: '#B45309',
    bgColor: '#FFFBEB',
    borderColor: '#FDE68A'
  }
}

export default function ProvenanceBadge({
  type = 'source_extracted',
  source,
  documentId,
  filename,
  page,
  snippet,
  confidence,
  method,
  notes,
  size = 'normal',
  showSource = false,
  interactive = true,
  className = ''
}) {
  const [isOpen, setIsOpen] = useState(false)
  const popoverRef = useRef(null)

  const normalizedType = String(type).toLowerCase().replace('-', '_')
  const config = PROVENANCE_CONFIG[normalizedType] || PROVENANCE_CONFIG.source_extracted

  // Formatted source string
  let displaySource = source
  if (!displaySource) {
    if (config.key === 'user_provided') {
      displaySource = 'patient intake'
    } else if (config.key === 'ai_generated') {
      displaySource = 'Generated from available structured information'
    } else if (config.key === 'user_verified') {
      displaySource = notes ? `Edited & confirmed (${notes})` : 'Edited and confirmed by user'
    } else if (filename) {
      displaySource = `${filename}${page ? `, page ${page}` : ''}`
    } else {
      displaySource = config.defaultSource
    }
  }

  // Close popover on outside click
  useEffect(() => {
    function handleClickOutside(e) {
      if (popoverRef.current && !popoverRef.current.contains(e.target)) {
        setIsOpen(false)
      }
    }
    if (isOpen) {
      document.addEventListener('mousedown', handleClickOutside)
    }
    return () => {
      document.removeEventListener('mousedown', handleClickOutside)
    }
  }, [isOpen])

  const hasDetailedMetadata = Boolean(
    documentId || filename || page || snippet || confidence != null || method || notes
  )

  const isSmall = size === 'small'

  return (
    <span
      ref={popoverRef}
      style={{
        position: 'relative',
        display: 'inline-flex',
        alignItems: 'center',
        verticalAlign: 'middle'
      }}
      className={className}
    >
      <button
        type="button"
        onClick={() => {
          if (interactive && (hasDetailedMetadata || config.key === 'ai_generated' || config.key === 'user_provided')) {
            setIsOpen((prev) => !prev)
          }
        }}
        title={`Provenance: ${config.label} (${displaySource})`}
        style={{
          display: 'inline-flex',
          alignItems: 'center',
          gap: isSmall ? '0.35rem' : '0.45rem',
          padding: isSmall ? '0.12rem 0.45rem' : '0.2rem 0.6rem',
          fontSize: isSmall ? '11px' : '12px',
          fontWeight: 500,
          lineHeight: 1.3,
          color: config.textColor,
          backgroundColor: config.bgColor,
          border: `1px solid ${config.borderColor}`,
          borderRadius: '4px',
          cursor: interactive ? 'pointer' : 'default',
          textDecoration: 'none',
          outline: 'none',
          fontFamily: 'inherit',
          transition: 'all 0.1s ease'
        }}
      >
        {/* Subtle Restrained Dot */}
        <span
          style={{
            width: isSmall ? '5px' : '6px',
            height: isSmall ? '5px' : '6px',
            borderRadius: '50%',
            backgroundColor: config.dotColor,
            flexShrink: 0
          }}
        />

        {/* Label */}
        <span>{config.label}</span>

        {/* Optional Inline Source Text */}
        {showSource && (
          <span
            style={{
              color: 'var(--text-secondary)',
              fontSize: isSmall ? '10.5px' : '11px',
              marginLeft: '0.2rem',
              fontWeight: 400
            }}
          >
            · Source: {displaySource}
          </span>
        )}

        {/* Info indicator if clickable details exist */}
        {interactive && hasDetailedMetadata && (
          <span style={{ fontSize: '10px', opacity: 0.7, marginLeft: '0.15rem' }}>▾</span>
        )}
      </button>

      {/* Popover / Metadata Drawer */}
      {isOpen && (
        <div
          style={{
            position: 'absolute',
            top: 'calc(100% + 6px)',
            left: 0,
            zIndex: 1000,
            minWidth: '280px',
            maxWidth: '380px',
            backgroundColor: 'var(--bg-surface)',
            border: '1px solid var(--border-color)',
            borderRadius: '6px',
            boxShadow: '0 10px 25px -5px rgba(15, 23, 42, 0.15), 0 8px 10px -6px rgba(15, 23, 42, 0.1)',
            padding: '0.85rem 1rem',
            textAlign: 'left',
            color: 'var(--text-primary)',
            fontSize: '12.5px',
            lineHeight: 1.5
          }}
        >
          {/* Popover Header */}
          <div
            style={{
              display: 'flex',
              justifyContent: 'space-between',
              alignItems: 'center',
              borderBottom: '1px solid var(--border-subtle)',
              paddingBottom: '0.5rem',
              marginBottom: '0.5rem'
            }}
          >
            <div style={{ display: 'flex', alignItems: 'center', gap: '0.4rem' }}>
              <span
                style={{
                  width: '7px',
                  height: '7px',
                  borderRadius: '50%',
                  backgroundColor: config.dotColor
                }}
              />
              <strong style={{ color: config.textColor }}>{config.label} Provenance</strong>
            </div>
            <button
              type="button"
              onClick={(e) => {
                e.stopPropagation()
                setIsOpen(false)
              }}
              style={{
                background: 'none',
                border: 'none',
                fontSize: '14px',
                cursor: 'pointer',
                color: 'var(--text-muted)',
                padding: '0 0.25rem'
              }}
            >
              ✕
            </button>
          </div>

          {/* Source Description */}
          <div style={{ marginBottom: '0.5rem' }}>
            <div style={{ fontWeight: 600, color: 'var(--text-primary)' }}>
              Source: <span style={{ fontWeight: 400 }}>{displaySource}</span>
            </div>
            <div className="small muted" style={{ fontSize: '11.5px', marginTop: '0.2rem' }}>
              {config.defaultDescription}
            </div>
          </div>

          {/* Detailed Metadata Grid */}
          <div style={{ display: 'grid', gap: '0.35rem', fontSize: '11.5px', color: 'var(--text-secondary)' }}>
            {filename && (
              <div>
                <span className="muted">Source File:</span> <strong>{filename}</strong>
              </div>
            )}
            {page != null && (
              <div>
                <span className="muted">Page Number:</span> <strong>Page {page}</strong>
              </div>
            )}
            {documentId && (
              <div>
                <span className="muted">Document ID:</span> <code>{documentId}</code>
              </div>
            )}
            {confidence != null && (
              <div>
                <span className="muted">Extraction Confidence:</span>{' '}
                <strong>
                  {typeof confidence === 'number' && confidence <= 1
                    ? `${Math.round(confidence * 100)}%`
                    : confidence}
                </strong>
                <span style={{ fontSize: '10.5px', marginLeft: '0.25rem' }}>(Parsing certainty only)</span>
              </div>
            )}
            {method && (
              <div>
                <span className="muted">Extraction Method:</span> {method}
              </div>
            )}
            {notes && (
              <div>
                <span className="muted">Audit / Verification Note:</span> {notes}
              </div>
            )}
          </div>

          {/* Snippet Grounding */}
          {snippet && (
            <div
              style={{
                marginTop: '0.6rem',
                paddingTop: '0.5rem',
                borderTop: '1px dashed var(--border-subtle)'
              }}
            >
              <div className="small muted" style={{ fontWeight: 600, marginBottom: '0.25rem' }}>
                Grounding Excerpt from Report:
              </div>
              <div
                style={{
                  fontFamily: "'SF Mono', Consolas, Menlo, monospace",
                  fontSize: '11px',
                  backgroundColor: 'var(--bg-subtle)',
                  padding: '0.4rem 0.5rem',
                  borderRadius: '4px',
                  border: '1px solid var(--border-color)',
                  color: 'var(--text-primary)',
                  maxHeight: '80px',
                  overflowY: 'auto',
                  whiteSpace: 'pre-wrap'
                }}
              >
                "{snippet}"
              </div>
            </div>
          )}

          {/* Explicit Safety Notice for AI Generated */}
          {config.key === 'ai_generated' && (
            <div
              style={{
                marginTop: '0.6rem',
                padding: '0.4rem 0.5rem',
                backgroundColor: 'var(--status-info-bg)',
                borderRadius: '4px',
                fontSize: '11px',
                color: 'var(--brand-primary)',
                border: '1px solid var(--status-info-border)'
              }}
            >
              ℹ AI-generated synthesis. Does not constitute a diagnostic claim and did not appear verbatim in source reports.
            </div>
          )}
        </div>
      )}
    </span>
  )
}
