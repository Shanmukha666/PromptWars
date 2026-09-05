import React, { useState } from 'react'
import ProvenanceBadge from './ProvenanceBadge'

export default function TimelineHistoryPage({
  activePatient,
  onSelectDocument
}) {
  const documents = activePatient?.documents || []
  const [filterTest, setFilterTest] = useState('all')

  // Aggregate all unique test names across all reports for this patient
  const allTests = Array.from(
    new Set(
      documents.flatMap(d => Object.keys(d.extracted?.labs || {}))
    )
  )

  return (
    <div className="page-container stack gap-md">
      <div className="card">
        <div className="section-head">
          <div>
            <div style={{ display: 'flex', alignItems: 'center', gap: '0.5rem' }}>
              <h2>Patient Clinical Timeline & Report History</h2>
              <ProvenanceBadge type="source_extracted" size="small" />
            </div>
            <p className="small muted" style={{ marginTop: '0.25rem' }}>
              Chronological aggregation of laboratory observations across reports for <strong>{activePatient?.name || 'Selected Patient'}</strong>.
            </p>
          </div>
          {allTests.length > 0 && (
            <div style={{ display: 'flex', alignItems: 'center', gap: '0.5rem' }}>
              <label htmlFor="filter-test" style={{ margin: 0 }}>Filter Test:</label>
              <select
                id="filter-test"
                value={filterTest}
                onChange={e => setFilterTest(e.target.value)}
                style={{ background: 'var(--bg-surface)', color: 'var(--text-primary)', border: '1px solid var(--border-color)', borderRadius: '8px', padding: '0.4rem 0.8rem' }}
              >
                <option value="all">All Tests ({allTests.length})</option>
                {allTests.map(t => <option key={t} value={t}>{t}</option>)}
              </select>
            </div>
          )}
        </div>
      </div>

      {documents.length === 0 ? (
        <div className="card" style={{ padding: '2rem', textAlign: 'center' }}>
          <div className="muted small">No reports ingested for this patient yet. Ingest reports to construct the chronological timeline.</div>
        </div>
      ) : (
        <div className="timeline-container stack gap-md">
          {documents.map((doc, docIdx) => {
            const labs = doc.extracted?.labs || {}
            const matchedEntries = Object.entries(labs).filter(([k]) => filterTest === 'all' || filterTest === k)

            return (
              <div key={doc.document_id} className="card" style={{ position: 'relative', borderLeft: '4px solid var(--brand-primary)' }}>
                <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'flex-start', flexWrap: 'wrap', gap: '0.5rem' }}>
                  <div>
                    <div style={{ display: 'flex', alignItems: 'center', gap: '0.75rem' }}>
                      <span className="small muted" style={{ fontWeight: 600 }}>#{documents.length - docIdx}</span>
                      <strong style={{ fontSize: '15px', color: 'var(--text-primary)' }}>{doc.title}</strong>
                      <ProvenanceBadge
                        type="source_extracted"
                        filename={doc.title}
                        documentId={doc.document_id}
                        size="small"
                      />
                    </div>
                    <div className="small muted" style={{ marginTop: '0.2rem' }}>
                      Report Ingestion Date: {doc.created_at ? doc.created_at.slice(0, 10) : '—'}
                    </div>
                  </div>

                  <button
                    className="secondary-btn"
                    style={{ padding: '0.35rem 0.75rem', fontSize: '13px' }}
                    onClick={() => onSelectDocument(doc.document_id)}
                  >
                    Open Document →
                  </button>
                </div>

                {/* AI Summary snippet */}
                {doc.ai_summary?.summary && (
                  <div style={{ marginTop: '0.75rem', padding: '0.65rem 0.85rem', background: 'var(--bg-subtle)', borderRadius: 'var(--radius-input)', border: '1px solid var(--border-color)', fontSize: '13px' }}>
                    <div style={{ display: 'flex', justifyContent: 'space-between', marginBottom: '0.2rem' }}>
                      <span className="small muted" style={{ fontWeight: 600 }}>Summary at time of report:</span>
                      <ProvenanceBadge type="ai_generated" size="small" />
                    </div>
                    <div style={{ color: 'var(--text-primary)', lineHeight: '1.5' }}>{doc.ai_summary.summary}</div>
                  </div>
                )}

                {/* Observations in this report */}
                <div style={{ marginTop: '1rem' }}>
                  <div className="section-title mini">Documented Laboratory Observations</div>
                  {matchedEntries.length === 0 ? (
                    <div className="small muted">No matching lab values found in this report.</div>
                  ) : (
                    <div className="evidence-grid" style={{ marginTop: '0.5rem' }}>
                      {matchedEntries.map(([key, item]) => {
                        const isVerified = item.provenance_type === 'user_verified' || item.verification_status === 'verified'
                        return (
                          <div className="field-card" key={key}>
                            <div className="meta-row">
                              <strong style={{ fontSize: '14px', color: 'var(--text-primary)' }}>{item.test_name || key}</strong>
                              <div style={{ display: 'flex', gap: '0.35rem', alignItems: 'center' }}>
                                <span className={`pill ${item.status === 'low' ? 'low' : item.status === 'high' ? 'high' : item.status === 'normal' ? 'normal' : 'neutral'}`}>
                                  {item.status || 'not_assessed'}
                                </span>
                                <ProvenanceBadge
                                  type={isVerified ? 'user_verified' : 'source_extracted'}
                                  filename={doc.title}
                                  documentId={doc.document_id}
                                  page={item.source_page || 1}
                                  snippet={item.source_snippet}
                                  confidence={item.extraction_confidence}
                                  notes={item.verified_notes}
                                  size="small"
                                />
                              </div>
                            </div>

                            <div style={{ fontSize: '1.2rem', fontWeight: 600, color: 'var(--text-primary)', margin: '0.2rem 0' }}>
                              {item.value} <span style={{ fontSize: '13px', fontWeight: 400, color: 'var(--text-secondary)' }}>{item.unit}</span>
                            </div>

                            <div className="small muted">
                              {item.source_range_raw ? `Source ref: ${item.source_range_raw}` : (item.reference_range ? `${item.reference_range.min}–${item.reference_range.max} ${item.unit}` : 'Reference range not available in source report.')}
                            </div>
                          </div>
                        )
                      })}
                    </div>
                  )}
                </div>
              </div>
            )
          })}
        </div>
      )}
    </div>
  )
}