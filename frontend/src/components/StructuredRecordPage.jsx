import React, { useState, useMemo } from 'react'
import ProvenanceBadge from './ProvenanceBadge'
import { IconDoc, IconStructured, IconReview, IconTimeline, IconClose } from './Icons'

// Helper for restrained status rendering
function getStatusConfig(status, hasRefRange) {
  if (!hasRefRange || status === 'not_assessed' || !status) {
    return {
      label: 'Not assessed',
      dotColor: '#94A3B8',
      textColor: 'var(--text-secondary)',
      bgColor: 'var(--status-neutral-bg)',
      borderColor: 'var(--status-neutral-border)',
      note: 'No source range provided.'
    }
  }

  const s = String(status).toLowerCase()
  if (s === 'low') {
    return {
      label: 'Low',
      dotColor: 'var(--status-warning)',
      textColor: 'var(--status-warning)',
      bgColor: 'var(--status-warning-bg)',
      borderColor: 'var(--status-warning-border)',
      note: null
    }
  }
  if (s === 'normal' || s === 'within range' || s === 'within_range') {
    return {
      label: 'Within range',
      dotColor: 'var(--status-success)',
      textColor: 'var(--status-success)',
      bgColor: 'var(--status-success-bg)',
      borderColor: 'var(--status-success-border)',
      note: null
    }
  }
  if (s === 'high') {
    return {
      label: 'High',
      dotColor: 'var(--status-danger)',
      textColor: 'var(--status-danger)',
      bgColor: 'var(--status-danger-bg)',
      borderColor: 'var(--status-danger-border)',
      note: null
    }
  }

  return {
    label: 'Not assessed',
    dotColor: '#94A3B8',
    textColor: 'var(--text-secondary)',
    bgColor: 'var(--status-neutral-bg)',
    borderColor: 'var(--status-neutral-border)',
    note: 'No source range provided.'
  }
}

function getVerificationConfig(item) {
  const v = item.verification_status || (item.provenance_type === 'user_verified' ? 'verified' : 'unverified')
  if (v === 'verified' || item.provenance_type === 'user_verified') {
    return { label: 'Verified', badgeClass: 'user-verified' }
  }
  if (v === 'edited') {
    return { label: 'Edited', badgeClass: 'user-verified' }
  }
  if (item.provenance_type === 'source_extracted') {
    if (item.status === 'not_assessed' || (item.extraction_confidence != null && item.extraction_confidence < 0.85)) {
      return { label: 'Needs review', badgeClass: 'user-provided' }
    }
    return { label: 'AI extracted', badgeClass: 'source-extracted' }
  }
  return { label: 'AI extracted', badgeClass: 'ai-generated' }
}

export default function StructuredRecordPage({
  activePatient,
  activeDocument,
  onSelectDocument,
  onProceedToReview,
  onProceedToTimeline,
  onNavigateStage
}) {
  const [searchTerm, setSearchTerm] = useState('')
  const [statusFilter, setStatusFilter] = useState('all') // all, low, within_range, high, not_assessed
  const [reportFilter, setReportFilter] = useState('all') // all or docId
  const [verificationFilter, setVerificationFilter] = useState('all') // all, verified, needs_review, ai_extracted, edited
  const [sortOrder, setSortOrder] = useState('desc') // desc (newest first) or asc

  // Source Provenance Modal state
  const [activeSnippetModal, setActiveSnippetModal] = useState(null)

  const patientDocs = activePatient?.documents || []

  // Aggregate observations across patient reports
  const allObservations = useMemo(() => {
    const list = []
    patientDocs.forEach((doc) => {
      const labs = doc.extracted?.labs || {}
      Object.entries(labs).forEach(([key, item]) => {
        const hasRef = Boolean(
          (item.reference_range && item.reference_range.min != null && item.reference_range.max != null) ||
          (item.source_range_raw && item.source_range_raw.trim())
        )
        const statusConfig = getStatusConfig(item.status, hasRef)
        const verificationConfig = getVerificationConfig(item)

        list.push({
          key: `${doc.document_id}-${key}`,
          testKey: key,
          testName: item.test_name || key,
          value: item.value,
          unit: item.unit || '',
          sourceRangeRaw: item.source_range_raw || (item.reference_range ? `${item.reference_range.min}–${item.reference_range.max}` : null),
          hasRefRange: hasRef,
          statusConfig,
          statusCategory: statusConfig.label.toLowerCase().replace(' ', '_'),
          date: item.observation_date || (doc.created_at ? doc.created_at.slice(0, 10) : '—'),
          rawDate: doc.created_at || '1970-01-01',
          docId: doc.document_id,
          docTitle: doc.title,
          sourcePage: item.source_page || 1,
          sourceSnippet: item.source_snippet || 'Document text excerpted during observation parsing.',
          verificationConfig,
          provenanceType: item.provenance_type || 'source_extracted',
          rawItem: item
        })
      })
    })
    return list
  }, [patientDocs])

  // Filtered & Sorted Observations
  const filteredObservations = useMemo(() => {
    return allObservations
      .filter((obs) => {
        // Search
        if (searchTerm.trim()) {
          const q = searchTerm.toLowerCase()
          const matchName = obs.testName.toLowerCase().includes(q)
          const matchVal = String(obs.value).toLowerCase().includes(q)
          const matchUnit = obs.unit.toLowerCase().includes(q)
          const matchDoc = obs.docTitle.toLowerCase().includes(q)
          if (!matchName && !matchVal && !matchUnit && !matchDoc) return false
        }

        // Status Filter
        if (statusFilter !== 'all') {
          if (statusFilter === 'within_range' && obs.statusCategory !== 'within_range') return false
          if (statusFilter === 'low' && obs.statusCategory !== 'low') return false
          if (statusFilter === 'high' && obs.statusCategory !== 'high') return false
          if (statusFilter === 'not_assessed' && obs.statusCategory !== 'not_assessed') return false
        }

        // Report Filter
        if (reportFilter !== 'all' && obs.docId !== reportFilter) {
          return false
        }

        // Verification Filter
        if (verificationFilter !== 'all') {
          const v = obs.verificationConfig.label.toLowerCase().replace(' ', '_')
          if (verificationFilter !== v) return false
        }

        return true
      })
      .sort((a, b) => {
        const dateA = new Date(a.rawDate).getTime() || 0
        const dateB = new Date(b.rawDate).getTime() || 0
        return sortOrder === 'desc' ? dateB - dateA : dateA - dateB
      })
  }, [allObservations, searchTerm, statusFilter, reportFilter, verificationFilter, sortOrder])

  return (
    <div className="page-container stack gap-md">
      {/* Top Header Card */}
      <div className="card" style={{ padding: '1.25rem 1.5rem' }}>
        <div className="section-head">
          <div>
            <div style={{ display: 'flex', alignItems: 'center', gap: '0.65rem' }}>
              <IconStructured size={22} className="brand-text" />
              <h2 style={{ fontSize: '20px', margin: 0 }}>Structured Medical Record</h2>
              <ProvenanceBadge type="source_extracted" size="small" />
            </div>
            <p className="small muted" style={{ marginTop: '0.25rem', marginBottom: 0 }}>
              Synthesized, verifiable clinical observation table for <strong>{activePatient?.name || 'Selected Patient'}</strong>. Reference ranges and statuses strictly derive from source reports.
            </p>
          </div>
          <div style={{ display: 'flex', gap: '0.5rem' }}>
            <button className="secondary-btn btn-sm" onClick={onProceedToReview}>
              Audit & Verify &rarr;
            </button>
            <button className="primary-btn btn-sm" onClick={onProceedToTimeline}>
              View Timeline &rarr;
            </button>
          </div>
        </div>

        {/* Filter & Search Bar */}
        <div
          style={{
            display: 'flex',
            gap: '0.75rem',
            alignItems: 'center',
            flexWrap: 'wrap',
            marginTop: '1.25rem',
            paddingTop: '1rem',
            borderTop: '1px solid var(--border-subtle)'
          }}
        >
          {/* Search Input */}
          <div style={{ flex: '1 1 200px' }}>
            <input
              type="text"
              placeholder="Search by observation, value, or unit..."
              value={searchTerm}
              onChange={(e) => setSearchTerm(e.target.value)}
              style={{ fontSize: '13px', padding: '0.45rem 0.75rem', width: '100%' }}
            />
          </div>

          {/* Status Filter */}
          <div style={{ display: 'flex', alignItems: 'center', gap: '0.35rem' }}>
            <span className="small muted" style={{ whiteSpace: 'nowrap' }}>Status:</span>
            <select
              value={statusFilter}
              onChange={(e) => setStatusFilter(e.target.value)}
              style={{ fontSize: '13px', padding: '0.45rem 0.65rem', background: 'var(--bg-surface)' }}
            >
              <option value="all">All Statuses</option>
              <option value="low">Low</option>
              <option value="within_range">Within Range</option>
              <option value="high">High</option>
              <option value="not_assessed">Not Assessed</option>
            </select>
          </div>

          {/* Report Filter */}
          <div style={{ display: 'flex', alignItems: 'center', gap: '0.35rem' }}>
            <span className="small muted" style={{ whiteSpace: 'nowrap' }}>Report:</span>
            <select
              value={reportFilter}
              onChange={(e) => setReportFilter(e.target.value)}
              style={{ fontSize: '13px', padding: '0.45rem 0.65rem', background: 'var(--bg-surface)', maxWidth: '180px' }}
            >
              <option value="all">All Reports ({patientDocs.length})</option>
              {patientDocs.map((doc) => (
                <option key={doc.document_id} value={doc.document_id}>
                  {doc.title}
                </option>
              ))}
            </select>
          </div>

          {/* Verification Filter */}
          <div style={{ display: 'flex', alignItems: 'center', gap: '0.35rem' }}>
            <span className="small muted" style={{ whiteSpace: 'nowrap' }}>Verification:</span>
            <select
              value={verificationFilter}
              onChange={(e) => setVerificationFilter(e.target.value)}
              style={{ fontSize: '13px', padding: '0.45rem 0.65rem', background: 'var(--bg-surface)' }}
            >
              <option value="all">All States</option>
              <option value="verified">Verified</option>
              <option value="needs_review">Needs Review</option>
              <option value="ai_extracted">AI Extracted</option>
              <option value="edited">Edited</option>
            </select>
          </div>

          {/* Date Sort Toggle */}
          <button
            type="button"
            className="secondary-btn btn-sm"
            onClick={() => setSortOrder(prev => prev === 'desc' ? 'asc' : 'desc')}
            title="Toggle chronological sorting"
            style={{ fontSize: '12.5px', padding: '0.45rem 0.75rem' }}
          >
            Date: {sortOrder === 'desc' ? 'Newest (desc)' : 'Oldest (asc)'}
          </button>
        </div>
      </div>

      {/* Observation Table Card */}
      <div className="card" style={{ padding: 0, overflow: 'hidden' }}>
        <div style={{ overflowX: 'auto' }}>
          <table style={{ width: '100%', borderCollapse: 'collapse', textAlign: 'left', fontSize: '13.5px' }}>
            <thead>
              <tr style={{ background: 'var(--bg-subtle)', borderBottom: '1px solid var(--border-color)' }}>
                <th style={{ padding: '0.75rem 1rem', fontWeight: 600, color: 'var(--text-secondary)' }}>Test / Observation</th>
                <th style={{ padding: '0.75rem 0.75rem', fontWeight: 600, color: 'var(--text-secondary)', width: '90px' }}>Value</th>
                <th style={{ padding: '0.75rem 0.75rem', fontWeight: 600, color: 'var(--text-secondary)', width: '80px' }}>Unit</th>
                <th style={{ padding: '0.75rem 1rem', fontWeight: 600, color: 'var(--text-secondary)' }}>Reference Range</th>
                <th style={{ padding: '0.75rem 0.75rem', fontWeight: 600, color: 'var(--text-secondary)', width: '130px' }}>Status</th>
                <th style={{ padding: '0.75rem 0.75rem', fontWeight: 600, color: 'var(--text-secondary)', width: '100px' }}>Date</th>
                <th style={{ padding: '0.75rem 0.75rem', fontWeight: 600, color: 'var(--text-secondary)', width: '150px' }}>Source</th>
                <th style={{ padding: '0.75rem 1rem', fontWeight: 600, color: 'var(--text-secondary)', width: '120px' }}>Verification</th>
              </tr>
            </thead>
            <tbody>
              {filteredObservations.length === 0 ? (
                <tr>
                  <td colSpan={8} style={{ padding: '3rem 1.5rem', textAlign: 'center', color: 'var(--text-muted)' }}>
                    {allObservations.length === 0 ? (
                      <div>
                        <div style={{ fontWeight: 600, color: 'var(--text-primary)', marginBottom: '0.25rem' }}>
                          No structured observations available
                        </div>
                        <div className="small">
                          No laboratory observations have been extracted yet. Upload or select a clinical document to populate this table.
                        </div>
                      </div>
                    ) : (
                      <div>No clinical observations match the selected search and filter criteria.</div>
                    )}
                  </td>
                </tr>
              ) : (
                filteredObservations.map((obs) => {
                  return (
                    <tr
                      key={obs.key}
                      style={{
                        borderBottom: '1px solid var(--border-subtle)',
                        transition: 'background-color 0.1s ease'
                      }}
                      onMouseEnter={(e) => e.currentTarget.style.backgroundColor = 'var(--bg-subtle)'}
                      onMouseLeave={(e) => e.currentTarget.style.backgroundColor = 'transparent'}
                    >
                      {/* Test / Observation */}
                      <td style={{ padding: '0.65rem 1rem', fontWeight: 600, color: 'var(--text-primary)' }}>
                        {obs.testName}
                      </td>

                      {/* Value */}
                      <td style={{ padding: '0.65rem 0.75rem', fontWeight: 700, color: 'var(--text-primary)' }}>
                        {obs.value}
                      </td>

                      {/* Unit */}
                      <td style={{ padding: '0.65rem 0.75rem', color: 'var(--text-secondary)' }}>
                        {obs.unit || <span className="muted" style={{ fontStyle: 'italic' }}>—</span>}
                      </td>

                      {/* Reference Range */}
                      <td style={{ padding: '0.65rem 1rem', color: 'var(--text-secondary)' }}>
                        {obs.hasRefRange ? (
                          <span>{obs.sourceRangeRaw} {obs.unit}</span>
                        ) : (
                          <span style={{ color: 'var(--text-muted)', fontStyle: 'italic', fontSize: '12.5px' }}>
                            No source range provided.
                          </span>
                        )}
                      </td>

                      {/* Restrained Status Indicator */}
                      <td style={{ padding: '0.65rem 0.75rem' }}>
                        <span
                          style={{
                            display: 'inline-flex',
                            alignItems: 'center',
                            gap: '0.4rem',
                            fontSize: '12.5px',
                            fontWeight: 600,
                            color: obs.statusConfig.textColor,
                            backgroundColor: obs.statusConfig.bgColor,
                            border: `1px solid ${obs.statusConfig.borderColor}`,
                            borderRadius: '4px',
                            padding: '0.15rem 0.5rem'
                          }}
                        >
                          <span style={{ width: '6px', height: '6px', borderRadius: '50%', backgroundColor: obs.statusConfig.dotColor }} />
                          {obs.statusConfig.label}
                        </span>
                      </td>

                      {/* Date */}
                      <td style={{ padding: '0.65rem 0.75rem', color: 'var(--text-secondary)', fontSize: '12.5px' }}>
                        {obs.date}
                      </td>

                      {/* Source Reference Link */}
                      <td style={{ padding: '0.65rem 0.75rem' }}>
                        <button
                          type="button"
                          className="btn-link"
                          onClick={() => setActiveSnippetModal(obs)}
                          style={{
                            background: 'none',
                            border: 'none',
                            padding: 0,
                            color: 'var(--brand-primary)',
                            fontSize: '12.5px',
                            cursor: 'pointer',
                            textAlign: 'left',
                            display: 'flex',
                            flexDirection: 'column'
                          }}
                          title="Inspect report provenance snippet"
                        >
                          <span style={{ textDecoration: 'underline', fontWeight: 500, maxWidth: '140px', overflow: 'hidden', textOverflow: 'ellipsis', whiteSpace: 'nowrap' }}>
                            {obs.docTitle}
                          </span>
                          <span className="small muted">Page {obs.sourcePage} &rarr;</span>
                        </button>
                      </td>

                      {/* Verification State & Detailed Provenance */}
                      <td style={{ padding: '0.65rem 1rem' }}>
                        <ProvenanceBadge
                          type={obs.provenanceType || (obs.verificationConfig.label === 'Verified' ? 'user_verified' : 'source_extracted')}
                          documentId={obs.docId}
                          filename={obs.docTitle}
                          page={obs.sourcePage}
                          snippet={obs.sourceSnippet}
                          confidence={obs.rawItem?.extraction_confidence}
                          notes={obs.rawItem?.verified_notes}
                          size="small"
                        />
                      </td>
                    </tr>
                  )
                })
              )}
            </tbody>
          </table>
        </div>

        {/* Footer info banner */}
        <div style={{ padding: '0.75rem 1rem', background: 'var(--bg-subtle)', borderTop: '1px solid var(--border-color)', display: 'flex', justifyContent: 'space-between', alignItems: 'center', fontSize: '12.5px', color: 'var(--text-secondary)' }}>
          <span>
            Showing <strong>{filteredObservations.length}</strong> of <strong>{allObservations.length}</strong> observations
          </span>
          <span style={{ fontStyle: 'italic' }}>
            MedLens strictly adheres to source report reference ranges. Ranges are never hallucinated or assumed.
          </span>
        </div>
      </div>

      {/* Source Provenance Snippet Modal */}
      {activeSnippetModal && (
        <div
          className="modal-backdrop"
          onClick={() => setActiveSnippetModal(null)}
          style={{
            position: 'fixed',
            inset: 0,
            backgroundColor: 'rgba(15, 23, 42, 0.45)',
            display: 'flex',
            alignItems: 'center',
            justifyContent: 'center',
            zIndex: 9999,
            padding: '1rem'
          }}
        >
          <div
            className="modal-card card"
            onClick={(e) => e.stopPropagation()}
            style={{
              width: '100%',
              maxWidth: '560px',
              padding: '1.5rem',
              backgroundColor: 'var(--bg-surface)',
              borderRadius: 'var(--radius-card)',
              boxShadow: '0 20px 25px -5px rgba(0, 0, 0, 0.1), 0 8px 10px -6px rgba(0, 0, 0, 0.1)'
            }}
          >
            <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'flex-start', marginBottom: '1rem' }}>
              <div>
                <div style={{ display: 'flex', alignItems: 'center', gap: '0.5rem' }}>
                  <IconDoc size={20} className="brand-text" />
                  <h3 style={{ margin: 0, fontSize: '17px', color: 'var(--text-primary)' }}>Source Provenance Verification</h3>
                </div>
                <div className="small muted" style={{ marginTop: '0.2rem' }}>
                  Verifiable document excerpt for <strong>{activeSnippetModal.testName}</strong>
                </div>
              </div>
              <button
                type="button"
                onClick={() => setActiveSnippetModal(null)}
                style={{ background: 'none', border: 'none', cursor: 'pointer', color: 'var(--text-muted)' }}
              >
                <IconClose size={20} />
              </button>
            </div>

            <div className="stack gap-sm" style={{ marginBottom: '1.25rem' }}>
              <div style={{ padding: '0.65rem 0.85rem', background: 'var(--bg-subtle)', borderRadius: 'var(--radius-input)', border: '1px solid var(--border-color)', display: 'grid', gridTemplateColumns: '1fr 1fr', gap: '0.5rem', fontSize: '13px' }}>
                <div><strong>Document:</strong> {activeSnippetModal.docTitle}</div>
                <div><strong>Source Page:</strong> Page {activeSnippetModal.sourcePage}</div>
                <div><strong>Extracted Value:</strong> {activeSnippetModal.value} {activeSnippetModal.unit}</div>
                <div><strong>Source Reference:</strong> {activeSnippetModal.hasRefRange ? activeSnippetModal.sourceRangeRaw : 'None provided'}</div>
              </div>

              <div>
                <label className="small muted" style={{ fontWeight: 600, display: 'block', marginBottom: '0.25rem' }}>
                  Exact Text Excerpt from Source Document:
                </label>
                <div
                  style={{
                    padding: '0.85rem 1rem',
                    background: 'var(--bg-subtle)',
                    borderRadius: 'var(--radius-input)',
                    border: '1px solid var(--border-color)',
                    fontFamily: 'monospace',
                    fontSize: '12.5px',
                    lineHeight: '1.5',
                    color: 'var(--text-primary)',
                    maxHeight: '160px',
                    overflowY: 'auto'
                  }}
                >
                  "{activeSnippetModal.sourceSnippet}"
                </div>
              </div>
            </div>

            <div style={{ display: 'flex', justifyContent: 'flex-end', gap: '0.5rem' }}>
              {onSelectDocument && (
                <button
                  className="secondary-btn btn-sm"
                  onClick={() => {
                    onSelectDocument(activeSnippetModal.docId)
                    setActiveSnippetModal(null)
                  }}
                >
                  Open Full Report
                </button>
              )}
              <button
                className="primary-btn btn-sm"
                onClick={() => setActiveSnippetModal(null)}
              >
                Close Provenance Viewer
              </button>
            </div>
          </div>
        </div>
      )}
    </div>
  )
}
