import React from 'react'
import ProvenanceBadge from './ProvenanceBadge'
import { IconPatient, IconReports, IconReview, IconTimeline, IconStructured } from './Icons'

export default function OverviewPage({
  patients = [],
  activePatient,
  onSelectPatient,
  onNewPatient,
  documents = [],
  health,
  onProceedToProfile,
  onSelectDocument,
  onNavigateStage
}) {
  // If no patient is selected, display helpful empty/selection state with patient directory
  if (!activePatient) {
    return (
      <div className="page-container stack gap-md">
        <div className="card overview-empty-state">
          <div className="overview-empty-mark" aria-hidden="true">
            <IconPatient size={32} />
          </div>
          <div className="overview-empty-copy">
            <span className="eyebrow">Clinical workspace</span>
            <h2>No patient context selected</h2>
            <p className="small muted">
              Choose a record from the directory or create a new patient context to begin reviewing clinical evidence.
            </p>
            <button onClick={onNewPatient} className="primary-btn">
              + Intake New Patient
            </button>
          </div>
          <div className="overview-empty-metrics" aria-label="Workspace overview">
            <div><strong>{patients.length}</strong><span>Patients</span></div>
            <div><strong>{documents.length}</strong><span>Reports</span></div>
            <div><strong>Local</strong><span>Data mode</span></div>
          </div>
        </div>

        {/* Registered Patients Directory */}
        <div className="card tall">
          <div className="section-head">
            <div>
              <h3>Registered Patients Directory ({patients.length})</h3>
              <div className="small muted">Click any patient to open their comprehensive clinical record.</div>
            </div>
          </div>

          <div style={{ marginTop: '1rem' }}>
            {patients.length === 0 ? (
              <div className="muted small" style={{ padding: '2rem', textAlign: 'center' }}>
                No patient records exist yet in local storage. Click <strong>+ Intake New Patient</strong> to begin.
              </div>
            ) : (
              <div style={{ display: 'grid', gap: '0.75rem' }}>
                {patients.map((pat) => (
                  <div
                    key={pat.patient_id}
                    className="card patient-directory-row"
                    style={{
                      padding: '1rem',
                      cursor: 'pointer',
                      border: '1px solid var(--border-color)',
                      transition: 'border-color 0.15s, background-color 0.15s'
                    }}
                    onClick={() => onSelectPatient(pat.patient_id)}
                  >
                    <div className="patient-directory-details">
                      <div className="patient-directory-heading">
                        <strong style={{ fontSize: '15px', color: 'var(--text-primary)' }}>{pat.name}</strong>
                        <ProvenanceBadge type="user_provided" size="small" />
                      </div>
                      <div className="small muted patient-directory-meta" style={{ marginTop: '0.2rem' }}>
                        Age: {pat.age ?? 'Not specified'} · Sex: {pat.sex ?? 'Not specified'} · Registered: {pat.created_at ? pat.created_at.slice(0, 10) : '—'}
                      </div>
                    </div>
                    <button
                      className="secondary-btn btn-sm"
                      onClick={(e) => {
                        e.stopPropagation()
                        onSelectPatient(pat.patient_id)
                      }}
                    >
                      Open Record &rarr;
                    </button>
                  </div>
                ))}
              </div>
            )}
          </div>
        </div>
      </div>
    )
  }

  // Active Patient Exists: Calculate required sections
  const patientDocs = activePatient.documents || []
  const hasReports = patientDocs.length > 0
  
  // Most recent report
  const recentReport = hasReports ? patientDocs[0] : null
  const recentLabs = recentReport?.extracted?.labs || {}
  const recentLabEntries = Object.entries(recentLabs)
  const recentEntities = recentReport?.extracted?.entities || {}

  // Review items calculation across all reports or recent report
  const reviewItems = []
  patientDocs.forEach((doc) => {
    const labs = doc.extracted?.labs || {}
    Object.entries(labs).forEach(([key, item]) => {
      const isVerified = item.provenance_type === 'user_verified' || item.verification_status === 'verified'
      if (isVerified) return

      const issues = []
      // 1. Missing source range
      if (item.status === 'not_assessed' || !item.source_range_raw) {
        issues.push({
          type: 'missing_range',
          label: 'Missing Source Range',
          detail: 'No reference interval explicitly stated in source document.'
        })
      }
      // 2. Low confidence
      if (item.extraction_confidence != null && item.extraction_confidence < 0.85) {
        issues.push({
          type: 'low_confidence',
          label: 'Low Extraction Confidence',
          detail: `Confidence ${Math.round(item.extraction_confidence * 100)}% requires visual verification.`
        })
      }
      // 3. Unclear unit
      if (!item.unit || item.unit.trim() === '' || item.unit.toLowerCase() === 'unknown') {
        issues.push({
          type: 'unclear_unit',
          label: 'Unclear Unit',
          detail: 'No unit of measurement extracted from report text.'
        })
      }

      if (issues.length > 0) {
        reviewItems.push({
          docId: doc.document_id,
          docTitle: doc.title,
          testKey: key,
          testName: item.test_name || key,
          value: item.value,
          unit: item.unit,
          sourceSnippet: item.source_snippet,
          issues
        })
      }
    })
  })

  // Unresolved patient context
  const patientProfileIncomplete = !activePatient.age || !activePatient.sex || (!activePatient.symptoms?.length && !activePatient.conditions?.length)

  // Recent changes (Delta comparison between the latest two reports)
  const changes = []
  if (patientDocs.length >= 2) {
    const latestLabs = patientDocs[0].extracted?.labs || {}
    const prevLabs = patientDocs[1].extracted?.labs || {}

    Object.entries(latestLabs).forEach(([testKey, currentItem]) => {
      const prevItem = prevLabs[testKey]
      if (prevItem && typeof currentItem.value === 'number' && typeof prevItem.value === 'number') {
        const delta = Number((currentItem.value - prevItem.value).toFixed(2))
        if (delta !== 0) {
          changes.push({
            testName: currentItem.test_name || testKey,
            unit: currentItem.unit || '',
            previousValue: prevItem.value,
            currentValue: currentItem.value,
            delta,
            prevDate: patientDocs[1].created_at ? patientDocs[1].created_at.slice(0, 10) : 'Prev',
            currDate: patientDocs[0].created_at ? patientDocs[0].created_at.slice(0, 10) : 'Latest',
            status: currentItem.status
          })
        }
      }
    })
  }

  // AI Record Summary text
  const primarySummary = recentReport?.ai_summary?.summary || (
    hasReports 
      ? 'Extracted report information available. Detailed laboratory values and entities are structured below.'
      : 'Patient context documented. No medical laboratory reports have been uploaded or processed yet for this record.'
  )

  return (
    <div className="page-container stack gap-md">
      {/* 1. Overview Header */}
      <div className="card" style={{ padding: '1.25rem 1.5rem', background: 'var(--bg-surface)' }}>
        <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'flex-start', flexWrap: 'wrap', gap: '1rem' }}>
          <div>
            <div style={{ display: 'flex', alignItems: 'center', gap: '0.65rem' }}>
              <h2 style={{ fontSize: '24px', fontWeight: 700, margin: 0, color: 'var(--text-primary)' }}>
                {activePatient.name || 'Anonymous Patient Record'}
              </h2>
              <ProvenanceBadge type="user_provided" size="small" />
            </div>

            <div style={{ display: 'flex', alignItems: 'center', gap: '1rem', marginTop: '0.4rem', flexWrap: 'wrap' }}>
              <span className="small" style={{ color: 'var(--text-secondary)' }}>
                <strong>Age / Sex:</strong> {activePatient.age ? `${activePatient.age}y` : 'Not recorded'} · {activePatient.sex || 'Not recorded'}
              </span>
              <span className="small" style={{ color: 'var(--text-muted)' }}>•</span>
              <span className="small" style={{ color: 'var(--text-secondary)' }}>
                <strong>Last Updated:</strong> {activePatient.updated_at ? activePatient.updated_at.slice(0, 10) : (activePatient.created_at ? activePatient.created_at.slice(0, 10) : 'Today')}
              </span>
            </div>
          </div>

          <div style={{ display: 'flex', alignItems: 'center', gap: '0.5rem' }}>
            <span
              style={{
                display: 'inline-flex',
                alignItems: 'center',
                gap: '0.35rem',
                fontSize: '11.5px',
                fontWeight: 500,
                color: 'var(--status-info)',
                backgroundColor: 'var(--status-info-bg)',
                border: '1px solid var(--status-info-border)',
                borderRadius: '100px',
                padding: '0.25rem 0.65rem'
              }}
            >
              AI-assisted record
            </span>
            <button
              className="secondary-btn btn-sm"
              onClick={onProceedToProfile}
              title="Edit Patient Intake Details"
            >
              Edit Profile
            </button>
          </div>
        </div>
      </div>

      {/* 2. Structured AI Record Summary Card */}
      <div className="card" style={{ borderLeft: '4px solid var(--brand-primary)' }}>
        <div className="section-head" style={{ marginBottom: '0.85rem' }}>
          <div style={{ display: 'flex', alignItems: 'center', gap: '0.65rem' }}>
            <h3 style={{ margin: 0, fontSize: '17px', color: 'var(--text-primary)' }}>Structured Record Summary</h3>
            <ProvenanceBadge type="ai_generated" size="small" />
          </div>
          {hasReports && onNavigateStage && (
            <button
              className="secondary-btn btn-sm"
              onClick={() => onNavigateStage('structured')}
            >
              View Full Observation Table &rarr;
            </button>
          )}
        </div>

        {/* Section 1: Overview */}
        <div style={{ padding: '0.85rem 1rem', background: 'var(--bg-subtle)', borderRadius: 'var(--radius-input)', border: '1px solid var(--border-color)', marginBottom: '1rem' }}>
          <div style={{ fontSize: '11px', fontWeight: 700, textTransform: 'uppercase', letterSpacing: '0.5px', color: 'var(--brand-primary)', marginBottom: '0.35rem' }}>
            Overview
          </div>
          <p style={{ fontSize: '14px', lineHeight: '1.6', color: 'var(--text-primary)', margin: 0 }}>
            {recentReport?.ai_summary?.overview || primarySummary}
          </p>
        </div>

        {/* Section 2 & 3: Key findings and Outside source ranges in a responsive two-column grid */}
        <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fit, minmax(300px, 1fr))', gap: '0.85rem', marginBottom: '0.85rem' }}>
          {/* Key findings */}
          <div style={{ padding: '0.85rem 1rem', background: 'var(--bg-surface)', borderRadius: 'var(--radius-input)', border: '1px solid var(--border-color)' }}>
            <div style={{ display: 'flex', alignItems: 'center', gap: '0.4rem', marginBottom: '0.5rem' }}>
              <span style={{ width: '8px', height: '8px', borderRadius: '50%', background: 'var(--status-info)' }}></span>
              <span style={{ fontSize: '12px', fontWeight: 600, color: 'var(--text-primary)' }}>Key Findings</span>
            </div>
            {recentReport?.ai_summary?.key_findings?.length > 0 ? (
              <ul style={{ margin: 0, paddingLeft: '1.15rem', fontSize: '12.5px', color: 'var(--text-primary)', display: 'grid', gap: '0.35rem' }}>
                {recentReport.ai_summary.key_findings.map((pt, idx) => (
                  <li key={idx} style={{ lineHeight: '1.45' }}>{pt}</li>
                ))}
              </ul>
            ) : recentReport?.ai_summary?.bullet_points?.length > 0 ? (
              <ul style={{ margin: 0, paddingLeft: '1.15rem', fontSize: '12.5px', color: 'var(--text-primary)', display: 'grid', gap: '0.35rem' }}>
                {recentReport.ai_summary.bullet_points.map((pt, idx) => (
                  <li key={idx} style={{ lineHeight: '1.45' }}>{pt}</li>
                ))}
              </ul>
            ) : (
              <div className="small muted">No key observation bullet points documented.</div>
            )}
          </div>

          {/* Outside source ranges */}
          <div style={{ padding: '0.85rem 1rem', background: recentReport?.ai_summary?.outside_source_ranges?.length > 0 ? 'var(--status-warning-bg)' : 'var(--bg-surface)', borderRadius: 'var(--radius-input)', border: `1px solid ${recentReport?.ai_summary?.outside_source_ranges?.length > 0 ? 'var(--status-warning-border)' : 'var(--border-color)'}` }}>
            <div style={{ display: 'flex', alignItems: 'center', gap: '0.4rem', marginBottom: '0.5rem' }}>
              <span style={{ width: '8px', height: '8px', borderRadius: '50%', background: recentReport?.ai_summary?.outside_source_ranges?.length > 0 ? 'var(--status-warning)' : 'var(--status-success)' }}></span>
              <span style={{ fontSize: '12px', fontWeight: 600, color: recentReport?.ai_summary?.outside_source_ranges?.length > 0 ? 'var(--status-warning)' : 'var(--text-primary)' }}>
                Outside Source Ranges
              </span>
            </div>
            {recentReport?.ai_summary?.outside_source_ranges?.length > 0 ? (
              <ul style={{ margin: 0, paddingLeft: '1.15rem', fontSize: '12.5px', color: 'var(--text-primary)', display: 'grid', gap: '0.35rem' }}>
                {recentReport.ai_summary.outside_source_ranges.map((pt, idx) => (
                  <li key={idx} style={{ lineHeight: '1.45' }}>{pt}</li>
                ))}
              </ul>
            ) : (
              <div className="small muted">All evaluated observations fall within source-provided reference intervals.</div>
            )}
          </div>
        </div>

        {/* Section 4 & 5: Medication/Allergy Info and Items Needing Review */}
        <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fit, minmax(300px, 1fr))', gap: '0.85rem', marginBottom: '0.85rem' }}>
          {/* Medication / Allergy information */}
          <div style={{ padding: '0.85rem 1rem', background: 'var(--bg-surface)', borderRadius: 'var(--radius-input)', border: '1px solid var(--border-color)' }}>
            <div style={{ display: 'flex', alignItems: 'center', gap: '0.4rem', marginBottom: '0.5rem' }}>
              <span style={{ width: '8px', height: '8px', borderRadius: '50%', background: 'var(--brand-primary)' }}></span>
              <span style={{ fontSize: '12px', fontWeight: 600, color: 'var(--text-primary)' }}>Medication / Allergy Record</span>
            </div>
            {recentReport?.ai_summary?.medication_allergy_info?.length > 0 ? (
              <ul style={{ margin: 0, paddingLeft: '1.15rem', fontSize: '12.5px', color: 'var(--text-primary)', display: 'grid', gap: '0.35rem' }}>
                {recentReport.ai_summary.medication_allergy_info.map((pt, idx) => (
                  <li key={idx} style={{ lineHeight: '1.45' }}>{pt}</li>
                ))}
              </ul>
            ) : (
              <div className="small muted">No medications or allergies documented in this report record.</div>
            )}
          </div>

          {/* Items needing review */}
          <div style={{ padding: '0.85rem 1rem', background: recentReport?.ai_summary?.items_needing_review?.length > 0 ? 'var(--status-neutral-bg)' : 'var(--bg-surface)', borderRadius: 'var(--radius-input)', border: '1px solid var(--border-color)' }}>
            <div style={{ display: 'flex', alignItems: 'center', gap: '0.4rem', marginBottom: '0.5rem' }}>
              <span style={{ width: '8px', height: '8px', borderRadius: '50%', background: '#64748B' }}></span>
              <span style={{ fontSize: '12px', fontWeight: 600, color: 'var(--text-primary)' }}>Items Needing Review</span>
            </div>
            {recentReport?.ai_summary?.items_needing_review?.length > 0 ? (
              <ul style={{ margin: 0, paddingLeft: '1.15rem', fontSize: '12.5px', color: 'var(--text-primary)', display: 'grid', gap: '0.35rem' }}>
                {recentReport.ai_summary.items_needing_review.map((pt, idx) => (
                  <li key={idx} style={{ lineHeight: '1.45' }}>{pt}</li>
                ))}
              </ul>
            ) : (
              <div className="small muted">No missing reference ranges or extraction uncertainties detected.</div>
            )}
          </div>
        </div>

        {/* Section 6: Footer Disclaimer */}
        <div style={{
          marginTop: '0.75rem',
          padding: '0.65rem 1rem',
          background: 'var(--bg-subtle)',
          borderRadius: 'var(--radius-input)',
          border: '1px solid var(--border-color)',
          fontSize: '12px',
          color: 'var(--text-secondary)',
          display: 'flex',
          alignItems: 'center',
          gap: '0.5rem'
        }}>
          <span style={{ color: 'var(--brand-primary)', fontWeight: 'bold' }}>&#9432;</span>
          <span>{recentReport?.ai_summary?.footer || "MedLens organizes the information available in this record. It does not provide a diagnosis or treatment recommendation."}</span>
        </div>
      </div>

      {/* 3. Key Information Grid */}
      <div className="card">
        <div className="section-head" style={{ marginBottom: '0.85rem' }}>
          <div>
            <h3 style={{ margin: 0, fontSize: '16px' }}>Key Information</h3>
            <div className="small muted">Documented baseline clinical context and intake history.</div>
          </div>
          <ProvenanceBadge type="user_provided" size="small" />
        </div>

        <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fit, minmax(210px, 1fr))', gap: '1rem' }}>
          {/* Active Symptoms */}
          <div style={{ padding: '0.85rem', background: 'var(--bg-subtle)', borderRadius: 'var(--radius-input)', border: '1px solid var(--border-color)' }}>
            <div className="small muted" style={{ fontWeight: 600, marginBottom: '0.4rem' }}>Active Symptoms</div>
            {activePatient.symptoms?.length > 0 ? (
              <div className="tag-wrap">
                {activePatient.symptoms.map(s => <span className="tag" key={s}>{s}</span>)}
              </div>
            ) : (
              <span className="small muted" style={{ fontStyle: 'italic' }}>No active symptoms recorded</span>
            )}
          </div>

          {/* Existing Conditions */}
          <div style={{ padding: '0.85rem', background: 'var(--bg-subtle)', borderRadius: 'var(--radius-input)', border: '1px solid var(--border-color)' }}>
            <div className="small muted" style={{ fontWeight: 600, marginBottom: '0.4rem' }}>Existing Conditions</div>
            {activePatient.conditions?.length > 0 ? (
              <div className="tag-wrap">
                {activePatient.conditions.map(c => <span className="tag" key={c}>{c}</span>)}
              </div>
            ) : (
              <span className="small muted" style={{ fontStyle: 'italic' }}>No conditions recorded</span>
            )}
          </div>

          {/* Allergies */}
          <div style={{ padding: '0.85rem', background: 'var(--bg-subtle)', borderRadius: 'var(--radius-input)', border: '1px solid var(--border-color)' }}>
            <div className="small muted" style={{ fontWeight: 600, marginBottom: '0.4rem' }}>Allergies</div>
            {activePatient.allergies?.length > 0 ? (
              <div className="tag-wrap">
                {activePatient.allergies.map(a => (
                  <span
                    className="tag"
                    key={a}
                    style={{ background: 'var(--status-warning-bg)', borderColor: 'var(--status-warning-border)', color: 'var(--status-warning)', fontWeight: 500 }}
                  >
                    ? {a}
                  </span>
                ))}
              </div>
            ) : (
              <span className="small muted" style={{ fontStyle: 'italic' }}>No allergies recorded</span>
            )}
          </div>

          {/* Medications */}
          <div style={{ padding: '0.85rem', background: 'var(--bg-subtle)', borderRadius: 'var(--radius-input)', border: '1px solid var(--border-color)' }}>
            <div className="small muted" style={{ fontWeight: 600, marginBottom: '0.4rem' }}>Current Medications</div>
            {activePatient.medications?.length > 0 ? (
              <div className="tag-wrap">
                {activePatient.medications.map(m => <span className="tag secondary" key={m}>{m}</span>)}
              </div>
            ) : (
              <span className="small muted" style={{ fontStyle: 'italic' }}>No medications recorded</span>
            )}
          </div>

          {/* Reports Available */}
          <div style={{ padding: '0.85rem', background: 'var(--bg-subtle)', borderRadius: 'var(--radius-input)', border: '1px solid var(--border-color)' }}>
            <div className="small muted" style={{ fontWeight: 600, marginBottom: '0.4rem' }}>Reports Available</div>
            <div style={{ display: 'flex', alignItems: 'baseline', gap: '0.4rem' }}>
              <span style={{ fontSize: '1.4rem', fontWeight: 700, color: 'var(--text-primary)' }}>{patientDocs.length}</span>
              <span className="small muted">document{patientDocs.length === 1 ? '' : 's'} on file</span>
            </div>
          </div>
        </div>
      </div>

      {/* Two Column Section: Recent Report & Needs Review */}
      <div className="page-grid two-col">
        {/* 4. Recent Report Section */}
        <div className="card">
          <div className="section-head" style={{ marginBottom: '0.85rem' }}>
            <div style={{ display: 'flex', alignItems: 'center', gap: '0.5rem' }}>
              <IconReports size={18} />
              <h3 style={{ margin: 0, fontSize: '16px' }}>Recent Report</h3>
            </div>
            {hasReports && onNavigateStage && (
              <button
                className="secondary-btn btn-sm"
                onClick={() => onNavigateStage('reports')}
              >
                All Reports ({patientDocs.length}) ?
              </button>
            )}
          </div>

          {!recentReport ? (
            <div style={{ padding: '2rem 1rem', textAlign: 'center', background: 'var(--bg-subtle)', borderRadius: 'var(--radius-input)' }}>
              <div className="small muted" style={{ marginBottom: '0.75rem' }}>No clinical reports uploaded for this patient yet.</div>
              {onNavigateStage && (
                <button
                  className="primary-btn btn-sm"
                  onClick={() => onNavigateStage('reports')}
                >
                  + Upload Clinical Report
                </button>
              )}
            </div>
          ) : (
            <div className="stack gap-sm">
              <div style={{ padding: '0.85rem', background: 'var(--bg-subtle)', borderRadius: 'var(--radius-input)', border: '1px solid var(--border-color)' }}>
                <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: '0.35rem' }}>
                  <strong style={{ fontSize: '14.5px', color: 'var(--text-primary)' }}>{recentReport.title}</strong>
                  <ProvenanceBadge
                    type="source_extracted"
                    filename={recentReport.title}
                    documentId={recentReport.document_id}
                    size="small"
                  />
                </div>

                <div className="stack gap-sm" style={{ marginTop: '0.5rem' }}>
                  <div className="meta-row small">
                    <span className="muted">Report Date:</span>
                    <span>{recentReport.created_at ? recentReport.created_at.slice(0, 10) : 'Not recorded'}</span>
                  </div>
                  <div className="meta-row small">
                    <span className="muted">Processing Status:</span>
                    <strong style={{ color: recentReport.status === 'processed' || recentReport.status === 'success' ? 'var(--status-success)' : 'var(--brand-primary)' }}>
                      ? {recentReport.status || 'Processed'}
                    </strong>
                  </div>
                  <div className="meta-row small">
                    <span className="muted">Extracted Observations:</span>
                    <strong>{recentLabEntries.length} laboratory test(s)</strong>
                  </div>
                  <div className="meta-row small">
                    <span className="muted">Requiring Verification:</span>
                    <strong style={{ color: reviewItems.filter(r => r.docId === recentReport.document_id).length > 0 ? 'var(--status-warning)' : 'var(--status-success)' }}>
                      {reviewItems.filter(r => r.docId === recentReport.document_id).length} item(s)
                    </strong>
                  </div>
                </div>

                {onSelectDocument && (
                  <div style={{ marginTop: '0.75rem', paddingTop: '0.65rem', borderTop: '1px solid var(--border-subtle)', display: 'flex', justifyContent: 'flex-end' }}>
                    <button
                      className="primary-btn btn-sm"
                      onClick={() => onSelectDocument(recentReport.document_id)}
                    >
                      Inspect Report Record ?
                    </button>
                  </div>
                )}
              </div>
            </div>
          )}
        </div>

        {/* 5. Needs Review Section (Strictly Unresolved Items) */}
        <div className="card">
          <div className="section-head" style={{ marginBottom: '0.85rem' }}>
            <div style={{ display: 'flex', alignItems: 'center', gap: '0.5rem' }}>
              <IconReview size={18} />
              <h3 style={{ margin: 0, fontSize: '16px' }}>Needs Review</h3>
            </div>
            {reviewItems.length > 0 && onNavigateStage && (
              <button
                className="secondary-btn btn-sm"
                onClick={() => onNavigateStage('review')}
              >
                Open Review Workspace ?
              </button>
            )}
          </div>

          {reviewItems.length === 0 && !patientProfileIncomplete ? (
            <div style={{ padding: '2rem 1rem', textAlign: 'center', background: 'var(--status-success-bg)', border: '1px solid var(--status-success-border)', borderRadius: 'var(--radius-input)' }}>
              <div style={{ color: 'var(--status-success)', fontWeight: 600, fontSize: '13.5px' }}>? No pending review items</div>
              <div className="small muted" style={{ marginTop: '0.25rem' }}>
                All extracted laboratory parameters contain valid source ranges or have been verified by a clinician.
              </div>
            </div>
          ) : (
            <div className="stack gap-sm" style={{ maxHeight: '280px', overflowY: 'auto' }}>
              {/* Patient context discrepancy if applicable */}
              {patientProfileIncomplete && (
                <div style={{ padding: '0.65rem 0.85rem', background: 'var(--status-warning-bg)', border: '1px solid var(--status-warning-border)', borderRadius: 'var(--radius-input)' }}>
                  <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}>
                    <strong style={{ fontSize: '13px', color: 'var(--status-warning)' }}>Unresolved Patient Profile</strong>
                    <button className="secondary-btn btn-sm" onClick={onProceedToProfile} style={{ padding: '0.15rem 0.5rem' }}>
                      Complete
                    </button>
                  </div>
                  <div className="small muted" style={{ marginTop: '0.2rem' }}>
                    Baseline age, sex, or clinical symptoms have not been fully specified during intake.
                  </div>
                </div>
              )}

              {/* Lab Extraction review items */}
              {reviewItems.slice(0, 4).map((item, idx) => (
                <div
                  key={`${item.docId}-${item.testKey}-${idx}`}
                  style={{
                    padding: '0.65rem 0.85rem',
                    background: 'var(--bg-subtle)',
                    border: '1px solid var(--border-color)',
                    borderRadius: 'var(--radius-input)'
                  }}
                >
                  <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}>
                    <span style={{ fontSize: '13px', fontWeight: 600, color: 'var(--text-primary)' }}>
                      {item.testName} ({item.value} {item.unit})
                    </span>
                    <div className="tag-wrap">
                      {item.issues.map((iss, i) => (
                        <span
                          key={i}
                          className="badge badge-sm"
                          style={{
                            backgroundColor: iss.type === 'missing_range' ? 'var(--status-neutral-bg)' : 'var(--status-warning-bg)',
                            borderColor: iss.type === 'missing_range' ? 'var(--status-neutral-border)' : 'var(--status-warning-border)',
                            color: iss.type === 'missing_range' ? 'var(--text-secondary)' : 'var(--status-warning)'
                          }}
                          title={iss.detail}
                        >
                          {iss.label}
                        </span>
                      ))}
                    </div>
                  </div>
                  <div className="small muted" style={{ marginTop: '0.2rem' }}>
                    {item.issues[0]?.detail}
                  </div>
                </div>
              ))}

              {reviewItems.length > 4 && (
                <div className="small muted" style={{ textAlign: 'center', paddingTop: '0.25rem' }}>
                  +{reviewItems.length - 4} more items requiring review in the audit workspace.
                </div>
              )}
            </div>
          )}
        </div>
      </div>

      {/* 6. Recent Changes Section */}
      <div className="card">
        <div className="section-head" style={{ marginBottom: '0.85rem' }}>
          <div style={{ display: 'flex', alignItems: 'center', gap: '0.5rem' }}>
            <IconTimeline size={18} />
            <h3 style={{ margin: 0, fontSize: '16px' }}>Recent Changes Compared with Previous Reports</h3>
          </div>
          {changes.length > 0 && onNavigateStage && (
            <button
              className="secondary-btn btn-sm"
              onClick={() => onNavigateStage('timeline')}
            >
              Full Longitudinal History ?
            </button>
          )}
        </div>

        {patientDocs.length < 2 ? (
          <div style={{ padding: '1.5rem', textAlign: 'center', background: 'var(--bg-subtle)', borderRadius: 'var(--radius-input)' }}>
            <div className="small muted">
              Longitudinal comparison requires at least two uploaded reports for this patient.
              {patientDocs.length === 1 ? ' Only 1 report currently on file.' : ' No reports currently on file.'}
            </div>
          </div>
        ) : changes.length === 0 ? (
          <div style={{ padding: '1.5rem', textAlign: 'center', background: 'var(--bg-subtle)', borderRadius: 'var(--radius-input)' }}>
            <div className="small muted">
              No quantitative numeric laboratory value shifts detected between the two latest reports.
            </div>
          </div>
        ) : (
          <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fit, minmax(260px, 1fr))', gap: '0.85rem' }}>
            {changes.map((chg, idx) => {
              const isPositive = chg.delta > 0
              return (
                <div
                  key={idx}
                  style={{
                    padding: '0.85rem 1rem',
                    background: 'var(--bg-subtle)',
                    border: '1px solid var(--border-color)',
                    borderRadius: 'var(--radius-input)',
                    display: 'flex',
                    flexDirection: 'column',
                    gap: '0.35rem'
                  }}
                >
                  <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}>
                    <strong style={{ fontSize: '13.5px', color: 'var(--text-primary)' }}>{chg.testName}</strong>
                    <span
                      className="badge badge-sm"
                      style={{
                        backgroundColor: isPositive ? 'var(--status-info-bg)' : 'var(--status-neutral-bg)',
                        borderColor: isPositive ? 'var(--status-info-border)' : 'var(--status-neutral-border)',
                        color: isPositive ? 'var(--status-info)' : 'var(--text-secondary)',
                        fontWeight: 600
                      }}
                    >
                      {isPositive ? `+${chg.delta}` : chg.delta} {chg.unit}
                    </span>
                  </div>

                  <div style={{ display: 'flex', alignItems: 'center', gap: '0.6rem', fontSize: '13px', marginTop: '0.15rem' }}>
                    <span className="muted">{chg.prevValue} {chg.unit} ({chg.prevDate})</span>
                    <span style={{ color: 'var(--text-muted)' }}>?</span>
                    <strong style={{ color: 'var(--text-primary)' }}>{chg.currentValue} {chg.unit} ({chg.currDate})</strong>
                  </div>
                </div>
              )
            })}
          </div>
        )}
      </div>
    </div>
  )
}

