import React, { useState, useEffect, useRef, useMemo } from 'react'
import ProvenanceBadge from './ProvenanceBadge'
import {
  IconDoc,
  IconCheckCircle,
  IconClose,
  IconStructured,
  IconTimeline
} from './Icons'

// Helper to evaluate confidence semantics
// Confidence refers ONLY to extraction confidence, never medical confidence.
function getExtractionConfidenceConfig(item) {
  const conf = item.extraction_confidence != null ? item.extraction_confidence : 0.8
  const hasRefRange = Boolean(
    (item.reference_range && item.reference_range.min != null && item.reference_range.max != null) ||
    (item.source_range_raw && item.source_range_raw.trim())
  )

  if (conf >= 0.85 && hasRefRange) {
    return {
      category: 'high_confidence',
      label: 'High confidence',
      color: 'var(--brand-primary)',
      bg: 'var(--status-info-bg)',
      border: 'var(--status-info-border)',
      scorePercent: Math.round(conf * 100),
      reason: 'Standard test identifier and source reference range cleanly parsed.'
    }
  }

  return {
    category: 'review_suggested',
    label: 'Review suggested',
    color: 'var(--status-warning)',
    bg: 'var(--status-warning-bg)',
    border: 'var(--status-warning-border)',
    scorePercent: Math.round(conf * 100),
    reason: !hasRefRange
      ? 'No source reference range provided in report text.'
      : 'Lower extraction certainty or ambiguous test pattern.'
  }
}

// Helper to calculate status strictly against report's extracted reference range
function getStatusBadge(item) {
  const status = item.status
  const hasRefRange = Boolean(
    (item.reference_range && item.reference_range.min != null && item.reference_range.max != null) ||
    (item.source_range_raw && item.source_range_raw.trim())
  )

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

export default function ReviewVerificationPage({
  activePatient,
  activeDocument,
  onSelectDocument,
  onVerifyOrEditLab,
  onProceedToTimeline,
  onNavigateStage,
  loading
}) {
  const patientDocs = activePatient?.documents || []
  const currentDoc = activeDocument || (patientDocs.length > 0 ? patientDocs[0] : null)
  const labs = currentDoc?.extracted?.labs || {}
  const rawText = currentDoc?.raw_text || currentDoc?.preview_text || 'No raw document text available for this report.'

  const observationKeys = useMemo(() => Object.keys(labs), [labs])

  // Active selected observation for inspection
  const [selectedKey, setSelectedKey] = useState(null)

  // Keep first item selected by default or update if key exists
  useEffect(() => {
    if (observationKeys.length > 0 && (!selectedKey || !labs[selectedKey])) {
      setSelectedKey(observationKeys[0])
    }
  }, [observationKeys, selectedKey, labs])

  const activeObs = selectedKey ? labs[selectedKey] : null

  // Document text search state
  const [docSearchTerm, setDocSearchTerm] = useState('')

  // Modal / action states
  const [isEditing, setIsEditing] = useState(false)
  const [isMarkingIncorrect, setIsMarkingIncorrect] = useState(false)
  const [isAddingMissing, setIsAddingMissing] = useState(false)
  const [isConfirmingRemove, setIsConfirmingRemove] = useState(false)
  const [toastMessage, setToastMessage] = useState('')

  // Edit form state
  const [editForm, setEditForm] = useState({
    value: '',
    unit: '',
    reference_range_raw: '',
    parsed_min: '',
    parsed_max: '',
    notes: ''
  })

  // Mark incorrect form state
  const [markIncorrectNotes, setMarkIncorrectNotes] = useState('')

  // Add missing observation form state
  const [addForm, setAddForm] = useState({
    test_name: '',
    value: '',
    unit: '',
    reference_range_raw: '',
    parsed_min: '',
    parsed_max: '',
    source_page: '1',
    source_snippet: '',
    notes: ''
  })

  // Ref for the document text container to handle auto-scrolling
  const docViewerRef = useRef(null)
  const highlightRef = useRef(null)

  // Auto-scroll to highlight when active observation changes
  useEffect(() => {
    if (highlightRef.current) {
      highlightRef.current.scrollIntoView({ behavior: 'smooth', block: 'center' })
    }
  }, [selectedKey, activeObs])

  function showToast(msg) {
    setToastMessage(msg)
    setTimeout(() => setToastMessage(''), 3500)
  }

  // --- ACTIONS ---

  // 1. Verify Correct
  async function handleVerify(key, item) {
    if (!currentDoc?.document_id) return
    try {
      await onVerifyOrEditLab({
        document_id: currentDoc.document_id,
        test_name: key,
        action: 'verify',
        value: item.value,
        unit: item.unit,
        reference_range_raw: item.source_range_raw,
        parsed_min: item.parsed_min ?? item.reference_range?.min ?? null,
        parsed_max: item.parsed_max ?? item.reference_range?.max ?? null,
        verification_status: 'verified',
        notes: 'Clinician confirmed extracted value & source snippet.'
      })
      showToast(`Verified ${key.toUpperCase()} as User-Verified.`)
    } catch (err) {
      showToast(`Error verifying observation: ${err.message}`)
    }
  }

  // 2. Open Edit Form
  function openEditModal(key, item) {
    setEditForm({
      value: item.value != null ? String(item.value) : '',
      unit: item.unit || '',
      reference_range_raw: item.source_range_raw || '',
      parsed_min: item.parsed_min != null ? String(item.parsed_min) : (item.reference_range?.min != null ? String(item.reference_range.min) : ''),
      parsed_max: item.parsed_max != null ? String(item.parsed_max) : (item.reference_range?.max != null ? String(item.reference_range.max) : ''),
      notes: ''
    })
    setIsEditing(true)
  }

  // Submit Edit
  async function handleSaveEdit() {
    if (!currentDoc?.document_id || !selectedKey) return
    const numVal = parseFloat(editForm.value)
    if (isNaN(numVal)) {
      alert('Please enter a valid numeric value.')
      return
    }

    const pMin = editForm.parsed_min ? parseFloat(editForm.parsed_min) : null
    const pMax = editForm.parsed_max ? parseFloat(editForm.parsed_max) : null

    try {
      await onVerifyOrEditLab({
        document_id: currentDoc.document_id,
        test_name: selectedKey,
        action: 'edit',
        value: numVal,
        unit: editForm.unit,
        reference_range_raw: editForm.reference_range_raw || null,
        parsed_min: pMin,
        parsed_max: pMax,
        verification_status: 'edited',
        notes: editForm.notes || 'Corrected by clinician during audit review.'
      })
      setIsEditing(false)
      showToast(`Updated and preserved audit trail for ${selectedKey.toUpperCase()}.`)
    } catch (err) {
      showToast(`Error saving edit: ${err.message}`)
    }
  }

  // 3. Mark Incorrect
  async function handleConfirmMarkIncorrect() {
    if (!currentDoc?.document_id || !selectedKey) return
    try {
      await onVerifyOrEditLab({
        document_id: currentDoc.document_id,
        test_name: selectedKey,
        action: 'mark_incorrect',
        verification_status: 'marked_incorrect',
        notes: markIncorrectNotes || 'Marked incorrect / false positive by clinician.'
      })
      setIsMarkingIncorrect(false)
      setMarkIncorrectNotes('')
      showToast(`Marked ${selectedKey.toUpperCase()} as incorrect with recorded rationale.`)
    } catch (err) {
      showToast(`Error marking incorrect: ${err.message}`)
    }
  }

  // 4. Remove Observation
  async function handleConfirmRemove() {
    if (!currentDoc?.document_id || !selectedKey) return
    const keyToRemove = selectedKey
    try {
      await onVerifyOrEditLab({
        document_id: currentDoc.document_id,
        test_name: keyToRemove,
        action: 'remove'
      })
      setIsConfirmingRemove(false)
      showToast(`Removed observation ${keyToRemove.toUpperCase()}.`)
      const remaining = observationKeys.filter((k) => k !== keyToRemove)
      setSelectedKey(remaining.length > 0 ? remaining[0] : null)
    } catch (err) {
      showToast(`Error removing observation: ${err.message}`)
    }
  }

  // 5. Add Missing Observation
  async function handleSaveAddMissing() {
    if (!currentDoc?.document_id) return
    const cleanName = addForm.test_name.trim().toLowerCase()
    if (!cleanName) {
      alert('Observation name is required.')
      return
    }
    const numVal = parseFloat(addForm.value)
    if (isNaN(numVal)) {
      alert('Please enter a valid numeric measured value.')
      return
    }

    const pMin = addForm.parsed_min ? parseFloat(addForm.parsed_min) : null
    const pMax = addForm.parsed_max ? parseFloat(addForm.parsed_max) : null
    const pageNum = parseInt(addForm.source_page) || 1

    try {
      await onVerifyOrEditLab({
        document_id: currentDoc.document_id,
        test_name: cleanName,
        action: 'add',
        value: numVal,
        unit: addForm.unit,
        reference_range_raw: addForm.reference_range_raw || null,
        parsed_min: pMin,
        parsed_max: pMax,
        source_page: pageNum,
        source_snippet: addForm.source_snippet || 'Manually cited by clinician.',
        verification_status: 'verified',
        notes: addForm.notes || 'Manually added by clinician from source report.'
      })
      setIsAddingMissing(false)
      setAddForm({
        test_name: '',
        value: '',
        unit: '',
        reference_range_raw: '',
        parsed_min: '',
        parsed_max: '',
        source_page: '1',
        source_snippet: '',
        notes: ''
      })
      setSelectedKey(cleanName)
      showToast(`Added missing observation ${cleanName.toUpperCase()} to record.`)
    } catch (err) {
      showToast(`Error adding observation: ${err.message}`)
    }
  }

  // Quick statistics
  const stats = useMemo(() => {
    let verified = 0
    let reviewSuggested = 0
    let highConf = 0
    let markedIncorrect = 0

    Object.values(labs).forEach((item) => {
      if (item.verification_status === 'marked_incorrect') {
        markedIncorrect++
      } else if (item.verification_status === 'verified' || item.provenance_type === 'user_verified') {
        verified++
      } else {
        const conf = getExtractionConfidenceConfig(item)
        if (conf.category === 'review_suggested') {
          reviewSuggested++
        } else {
          highConf++
        }
      }
    })

    return { total: Object.keys(labs).length, verified, reviewSuggested, highConf, markedIncorrect }
  }, [labs])

  // --- RENDERING SOURCE DOCUMENT VIEWER WITH HIGHLIGHT ---
  const renderedDocumentText = useMemo(() => {
    if (!rawText) return null

    let target = docSearchTerm.trim()
    let isSnippetTarget = false

    if (!target && activeObs) {
      if (activeObs.source_snippet && activeObs.source_snippet.length > 5) {
        target = activeObs.source_snippet.trim()
        isSnippetTarget = true
      } else if (activeObs.test_name) {
        target = activeObs.test_name
        isSnippetTarget = true
      }
    }

    if (!target) {
      return (
        <pre
          style={{
            whiteSpace: 'pre-wrap',
            wordBreak: 'break-word',
            fontFamily: "'SF Mono', Consolas, 'Liberation Mono', Menlo, monospace",
            fontSize: '13px',
            lineHeight: 1.6,
            color: 'var(--text-primary)',
            margin: 0
          }}
        >
          {rawText}
        </pre>
      )
    }

    let matchIndex = rawText.toLowerCase().indexOf(target.toLowerCase())

    if (matchIndex === -1 && isSnippetTarget && activeObs?.test_name) {
      target = activeObs.test_name
      matchIndex = rawText.toLowerCase().indexOf(target.toLowerCase())
    }

    if (matchIndex === -1) {
      return (
        <div>
          {isSnippetTarget && (
            <div
              style={{
                marginBottom: '1rem',
                padding: '0.65rem 0.85rem',
                background: 'var(--status-warning-bg)',
                border: '1px solid var(--status-warning-border)',
                borderRadius: '6px',
                fontSize: '12.5px',
                color: 'var(--status-warning)'
              }}
            >
              <strong>Source Excerpt Citation:</strong> "{activeObs?.source_snippet || target}"
              <div className="small muted" style={{ marginTop: '0.2rem' }}>
                (Exact OCR match point formatted below in document stream)
              </div>
            </div>
          )}
          <pre
            style={{
              whiteSpace: 'pre-wrap',
              wordBreak: 'break-word',
              fontFamily: "'SF Mono', Consolas, 'Liberation Mono', Menlo, monospace",
              fontSize: '13px',
              lineHeight: 1.6,
              color: 'var(--text-primary)',
              margin: 0
            }}
          >
            {rawText}
          </pre>
        </div>
      )
    }

    const before = rawText.slice(0, matchIndex)
    const match = rawText.slice(matchIndex, matchIndex + target.length)
    const after = rawText.slice(matchIndex + target.length)

    return (
      <pre
        style={{
          whiteSpace: 'pre-wrap',
          wordBreak: 'break-word',
          fontFamily: "'SF Mono', Consolas, 'Liberation Mono', Menlo, monospace",
          fontSize: '13px',
          lineHeight: 1.6,
          color: 'var(--text-primary)',
          margin: 0
        }}
      >
        {before}
        <mark
          ref={highlightRef}
          style={{
            backgroundColor: '#FEF08A',
            color: '#854D0E',
            padding: '0.15rem 0.35rem',
            borderRadius: '4px',
            border: '1px solid #EAB308',
            fontWeight: 700,
            boxShadow: '0 0 0 2px rgba(234, 179, 8, 0.3)'
          }}
        >
          {match}
        </mark>
        {after}
      </pre>
    )
  }, [rawText, docSearchTerm, activeObs])

  return (
    <div className="page-container stack gap-md">
      {/* Top Header Card */}
      <div className="card" style={{ padding: '1.25rem 1.5rem' }}>
        <div className="section-head" style={{ marginBottom: '0.75rem' }}>
          <div>
            <div style={{ display: 'flex', alignItems: 'center', gap: '0.65rem' }}>
              <IconDoc size={22} className="brand-text" />
              <h2 style={{ fontSize: '20px', margin: 0 }}>Review Extraction Workspace</h2>
              <span className="badge user-verified">Side-by-Side Audit</span>
            </div>
            <p className="small muted" style={{ marginTop: '0.25rem', marginBottom: 0 }}>
              Verify and edit AI-extracted laboratory findings directly alongside the original report document.
              All modifications maintain an immutable audit trail.
            </p>
          </div>

          <div style={{ display: 'flex', gap: '0.5rem', alignItems: 'center', flexWrap: 'wrap' }}>
            {onNavigateStage && (
              <button
                className="secondary-btn btn-sm"
                onClick={() => onNavigateStage('structured')}
                style={{ display: 'inline-flex', alignItems: 'center', gap: '0.35rem' }}
              >
                <IconStructured size={15} /> Structured Record
              </button>
            )}
            <button
              className="primary-btn btn-sm"
              onClick={onProceedToTimeline}
              style={{ display: 'inline-flex', alignItems: 'center', gap: '0.35rem' }}
            >
              <IconTimeline size={15} /> View Timeline &rarr;
            </button>
          </div>
        </div>

        {/* Report Selector & Quick Metrics Bar */}
        <div
          style={{
            display: 'flex',
            justifyContent: 'space-between',
            alignItems: 'center',
            flexWrap: 'wrap',
            gap: '1rem',
            paddingTop: '0.75rem',
            borderTop: '1px solid var(--border-subtle)'
          }}
        >
          {/* Document Switcher */}
          <div style={{ display: 'flex', alignItems: 'center', gap: '0.6rem' }}>
            <span className="small muted" style={{ fontWeight: 600 }}>Active Report:</span>
            {patientDocs.length > 1 ? (
              <select
                value={currentDoc?.document_id || ''}
                onChange={(e) => onSelectDocument && onSelectDocument(e.target.value)}
                style={{
                  fontSize: '13px',
                  padding: '0.35rem 0.65rem',
                  fontWeight: 600,
                  color: 'var(--text-primary)',
                  backgroundColor: 'var(--bg-subtle)'
                }}
              >
                {patientDocs.map((doc) => (
                  <option key={doc.document_id} value={doc.document_id}>
                    {doc.title} ({doc.created_at ? doc.created_at.slice(0, 10) : 'Report'})
                  </option>
                ))}
              </select>
            ) : (
              <strong style={{ fontSize: '13.5px', color: 'var(--text-primary)' }}>
                {currentDoc?.title || 'No report selected'}
              </strong>
            )}
            {currentDoc?.created_at && (
              <span className="small muted">
                Ingested {currentDoc.created_at.slice(0, 10)}
              </span>
            )}
          </div>

          {/* Metrics Strip */}
          <div style={{ display: 'flex', gap: '0.75rem', alignItems: 'center', flexWrap: 'wrap' }}>
            <span className="small muted">
              Total: <strong>{stats.total}</strong>
            </span>
            <span
              style={{
                fontSize: '12px',
                padding: '0.15rem 0.5rem',
                borderRadius: '4px',
                backgroundColor: 'var(--status-success-bg)',
                color: 'var(--status-success)',
                fontWeight: 600,
                border: '1px solid var(--status-success-border)'
              }}
            >
              ✓ {stats.verified} Verified
            </span>
            <span
              style={{
                fontSize: '12px',
                padding: '0.15rem 0.5rem',
                borderRadius: '4px',
                backgroundColor: 'var(--status-warning-bg)',
                color: 'var(--status-warning)',
                fontWeight: 600,
                border: '1px solid var(--status-warning-border)'
              }}
            >
              ⚠ {stats.reviewSuggested} Review Suggested
            </span>
            {stats.markedIncorrect > 0 && (
              <span
                style={{
                  fontSize: '12px',
                  padding: '0.15rem 0.5rem',
                  borderRadius: '4px',
                  backgroundColor: 'var(--status-danger-bg)',
                  color: 'var(--status-danger)',
                  fontWeight: 600,
                  border: '1px solid var(--status-danger-border)'
                }}
              >
                ✕ {stats.markedIncorrect} Incorrect
              </span>
            )}
            <button
              className="secondary-btn btn-sm"
              onClick={() => setIsAddingMissing(true)}
              style={{ fontSize: '12px', padding: '0.25rem 0.6rem' }}
            >
              + Add Missing Observation
            </button>
          </div>
        </div>

        {/* Toast Alert */}
        {toastMessage && (
          <div
            style={{
              marginTop: '0.75rem',
              padding: '0.5rem 0.85rem',
              background: 'var(--status-info-bg)',
              border: '1px solid var(--status-info-border)',
              borderRadius: '6px',
              color: 'var(--brand-primary)',
              fontSize: '13px',
              fontWeight: 500
            }}
          >
            ℹ {toastMessage}
          </div>
        )}
      </div>

      {/* Main Side-by-Side Workspace Grid */}
      <div
        style={{
          display: 'grid',
          gridTemplateColumns: 'minmax(0, 58%) minmax(0, 42%)',
          gap: '1rem',
          alignItems: 'start'
        }}
        className="review-split-workspace"
      >
        {/* LEFT COLUMN: 58% Source Document / Report Viewer */}
        <div
          className="card"
          style={{
            padding: 0,
            display: 'flex',
            flexDirection: 'column',
            height: 'calc(100vh - 270px)',
            minHeight: '620px',
            overflow: 'hidden'
          }}
        >
          {/* Document Viewer Header Bar */}
          <div
            style={{
              padding: '0.85rem 1.25rem',
              background: 'var(--bg-subtle)',
              borderBottom: '1px solid var(--border-color)',
              display: 'flex',
              justifyContent: 'space-between',
              alignItems: 'center',
              flexWrap: 'wrap',
              gap: '0.5rem'
            }}
          >
            <div style={{ display: 'flex', alignItems: 'center', gap: '0.5rem' }}>
              <IconDoc size={18} className="brand-text" />
              <strong style={{ fontSize: '14px', color: 'var(--text-primary)' }}>
                Source Document Viewer
              </strong>
              <span className="small muted">
                (Page {activeObs?.source_page || 1})
              </span>
            </div>

            {/* In-Document Search Bar & Jump Button */}
            <div style={{ display: 'flex', gap: '0.5rem', alignItems: 'center' }}>
              <input
                type="text"
                placeholder="Search text in report..."
                value={docSearchTerm}
                onChange={(e) => setDocSearchTerm(e.target.value)}
                style={{
                  fontSize: '12px',
                  padding: '0.3rem 0.6rem',
                  width: '180px',
                  background: 'var(--bg-surface)'
                }}
              />
              <button
                type="button"
                className="secondary-btn btn-sm"
                onClick={() => {
                  if (highlightRef.current) {
                    highlightRef.current.scrollIntoView({ behavior: 'smooth', block: 'center' })
                  }
                }}
                style={{ fontSize: '12px', padding: '0.3rem 0.55rem' }}
                title="Scroll document viewer to active observation snippet"
              >
                Jump to Snippet
              </button>
            </div>
          </div>

          {/* Document View Stream */}
          <div
            ref={docViewerRef}
            style={{
              padding: '1.25rem',
              overflowY: 'auto',
              flex: 1,
              backgroundColor: 'var(--bg-surface)'
            }}
          >
            {renderedDocumentText}
          </div>

          {/* Document Viewer Footer Note */}
          <div
            style={{
              padding: '0.5rem 1.25rem',
              background: 'var(--bg-subtle)',
              borderTop: '1px solid var(--border-color)',
              fontSize: '12px',
              color: 'var(--text-secondary)',
              display: 'flex',
              justifyContent: 'space-between'
            }}
          >
            <span>Exact source text excerpted from report parser.</span>
            <span>Highlighted text grounds the active observation.</span>
          </div>
        </div>

        {/* RIGHT COLUMN: 42% Structured Extracted Fields & Audit Inspector */}
        <div
          style={{
            display: 'flex',
            flexDirection: 'column',
            gap: '1rem',
            height: 'calc(100vh - 270px)',
            minHeight: '620px',
            overflowY: 'auto'
          }}
        >
          {/* Observation Selector Strip */}
          <div className="card" style={{ padding: '0.85rem 1rem' }}>
            <div
              style={{
                display: 'flex',
                justifyContent: 'space-between',
                alignItems: 'center',
                marginBottom: '0.65rem'
              }}
            >
              <span className="small muted" style={{ fontWeight: 600 }}>
                Extracted Observations ({observationKeys.length})
              </span>
              <span className="small muted">Click to inspect & highlight</span>
            </div>

            {observationKeys.length === 0 ? (
              <div className="small muted" style={{ padding: '1rem', textAlign: 'center' }}>
                No laboratory observations found in this document.
              </div>
            ) : (
              <div
                style={{
                  display: 'flex',
                  gap: '0.5rem',
                  overflowX: 'auto',
                  paddingBottom: '0.35rem'
                }}
              >
                {observationKeys.map((key) => {
                  const item = labs[key]
                  const isSelected = key === selectedKey
                  const isVerified = item.verification_status === 'verified' || item.provenance_type === 'user_verified'
                  const isIncorrect = item.verification_status === 'marked_incorrect'

                  return (
                    <button
                      key={key}
                      type="button"
                      onClick={() => setSelectedKey(key)}
                      style={{
                        padding: '0.45rem 0.65rem',
                        borderRadius: '6px',
                        border: isSelected
                          ? '2px solid var(--brand-primary)'
                          : isIncorrect
                          ? '1px solid var(--status-danger-border)'
                          : isVerified
                          ? '1px solid var(--status-success-border)'
                          : '1px solid var(--border-color)',
                        backgroundColor: isSelected
                          ? 'var(--status-info-bg)'
                          : 'var(--bg-surface)',
                        cursor: 'pointer',
                        textAlign: 'left',
                        whiteSpace: 'nowrap',
                        display: 'flex',
                        flexDirection: 'column',
                        gap: '0.15rem',
                        transition: 'all 0.15s ease'
                      }}
                    >
                      <div style={{ display: 'flex', alignItems: 'center', gap: '0.35rem' }}>
                        <strong style={{ fontSize: '12.5px', color: 'var(--text-primary)' }}>
                          {item.test_name || key.toUpperCase()}
                        </strong>
                        {isVerified && <span style={{ color: 'var(--status-success)', fontSize: '12px' }}>✓</span>}
                        {isIncorrect && <span style={{ color: 'var(--status-danger)', fontSize: '12px' }}>✕</span>}
                      </div>
                      <div style={{ fontSize: '11.5px', color: 'var(--text-secondary)' }}>
                        {item.value} {item.unit}
                      </div>
                    </button>
                  )
                })}
              </div>
            )}
          </div>

          {/* Active Observation Inspection Card */}
          {activeObs ? (
            <div className="card" style={{ padding: '1.25rem', display: 'grid', gap: '1rem' }}>
              {/* Card Header with Name, Status & Confidence */}
              <div>
                <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'flex-start', gap: '0.5rem' }}>
                  <div>
                    <h3 style={{ margin: 0, fontSize: '18px', color: 'var(--text-primary)' }}>
                      {activeObs.test_name || selectedKey.toUpperCase()}
                    </h3>
                    <div style={{ display: 'flex', gap: '0.5rem', alignItems: 'center', marginTop: '0.35rem', flexWrap: 'wrap' }}>
                      {/* Status Tag */}
                      {(() => {
                        const sb = getStatusBadge(activeObs)
                        return (
                          <span
                            style={{
                              display: 'inline-flex',
                              alignItems: 'center',
                              gap: '0.35rem',
                              fontSize: '12px',
                              fontWeight: 600,
                              color: sb.textColor,
                              backgroundColor: sb.bgColor,
                              border: `1px solid ${sb.borderColor}`,
                              borderRadius: '4px',
                              padding: '0.15rem 0.45rem'
                            }}
                          >
                            <span style={{ width: '6px', height: '6px', borderRadius: '50%', backgroundColor: sb.dotColor }} />
                            {sb.label}
                          </span>
                        )
                      })()}

                      {/* Verification State */}
                      <ProvenanceBadge
                        type={activeObs.provenance_type || (activeObs.verification_status === 'verified' ? 'user_verified' : 'source_extracted')}
                        documentId={currentDoc?.document_id}
                        filename={currentDoc?.title}
                        page={activeObs.source_page || 1}
                        snippet={activeObs.source_snippet}
                        confidence={activeObs.extraction_confidence}
                        notes={activeObs.verified_notes}
                        size="small"
                      />

                      {activeObs.verification_status === 'edited' && (
                        <span className="badge badge-sm user-verified">Edited</span>
                      )}
                      {activeObs.verification_status === 'marked_incorrect' && (
                        <span
                          style={{
                            fontSize: '11px',
                            fontWeight: 600,
                            padding: '0.1rem 0.4rem',
                            backgroundColor: 'var(--status-danger-bg)',
                            color: 'var(--status-danger)',
                            border: '1px solid var(--status-danger-border)',
                            borderRadius: '4px'
                          }}
                        >
                          Marked Incorrect
                        </span>
                      )}
                    </div>
                  </div>

                  {/* Extraction Confidence Badge */}
                  {(() => {
                    const conf = getExtractionConfidenceConfig(activeObs)
                    return (
                      <div
                        style={{
                          textAlign: 'right',
                          display: 'flex',
                          flexDirection: 'column',
                          alignItems: 'flex-end'
                        }}
                      >
                        <span
                          style={{
                            fontSize: '12px',
                            fontWeight: 600,
                            padding: '0.2rem 0.55rem',
                            borderRadius: '4px',
                            color: conf.color,
                            backgroundColor: conf.bg,
                            border: `1px solid ${conf.border}`
                          }}
                          title={conf.reason}
                        >
                          {conf.label}
                        </span>
                        <span className="small muted" style={{ fontSize: '10.5px', marginTop: '0.2rem' }}>
                          Extraction score: {conf.scorePercent}%
                        </span>
                      </div>
                    )
                  })()}
                </div>

                {/* Important Confidence Disclaimer */}
                <div
                  style={{
                    marginTop: '0.5rem',
                    padding: '0.4rem 0.65rem',
                    background: 'var(--bg-subtle)',
                    borderLeft: '3px solid var(--brand-primary)',
                    borderRadius: '0 4px 4px 0',
                    fontSize: '11.5px',
                    color: 'var(--text-secondary)'
                  }}
                >
                  <strong>Notice:</strong> Confidence reflects algorithmic extraction / OCR certainty only, never medical confidence or diagnostic probability.
                </div>
              </div>

              {/* Data Values Grid */}
              <div
                style={{
                  display: 'grid',
                  gridTemplateColumns: 'repeat(auto-fit, minmax(140px, 1fr))',
                  gap: '0.75rem',
                  padding: '0.85rem',
                  backgroundColor: 'var(--bg-subtle)',
                  borderRadius: '6px',
                  border: '1px solid var(--border-color)'
                }}
              >
                <div>
                  <div className="small muted">Extracted Value</div>
                  <div style={{ fontSize: '18px', fontWeight: 700, color: 'var(--text-primary)', marginTop: '0.15rem' }}>
                    {activeObs.value} {activeObs.unit}
                  </div>
                </div>

                <div>
                  <div className="small muted">Source Reference Range</div>
                  <div style={{ fontSize: '13px', fontWeight: 600, color: 'var(--text-primary)', marginTop: '0.25rem' }}>
                    {activeObs.source_range_raw ||
                      (activeObs.reference_range
                        ? `${activeObs.reference_range.min} - ${activeObs.reference_range.max} ${activeObs.unit}`
                        : <span style={{ color: 'var(--text-muted)', fontStyle: 'italic' }}>No source range provided.</span>)}
                  </div>
                </div>

                <div>
                  <div className="small muted">Observation Date</div>
                  <div style={{ fontSize: '13px', color: 'var(--text-primary)', marginTop: '0.25rem' }}>
                    {activeObs.observation_date || currentDoc?.created_at?.slice(0, 10) || '-'}
                  </div>
                </div>

                <div>
                  <div className="small muted">Source Location</div>
                  <div style={{ fontSize: '13px', color: 'var(--text-primary)', marginTop: '0.25rem' }}>
                    Page {activeObs.source_page || 1}
                  </div>
                </div>
              </div>

              {/* Source Snippet Grounding Box */}
              <div
                style={{
                  padding: '0.75rem 0.85rem',
                  backgroundColor: 'var(--bg-subtle)',
                  borderRadius: '6px',
                  border: '1px solid var(--border-color)'
                }}
              >
                <div style={{ display: 'flex', justifyContent: 'space-between', marginBottom: '0.25rem' }}>
                  <strong className="small muted" style={{ textTransform: 'uppercase', letterSpacing: '0.04em' }}>
                    Source Text Snippet:
                  </strong>
                  <span className="small muted">Page {activeObs.source_page || 1}</span>
                </div>
                <div
                  style={{
                    fontSize: '12.5px',
                    fontFamily: "'SF Mono', Consolas, Menlo, monospace",
                    color: 'var(--text-primary)',
                    backgroundColor: 'var(--bg-surface)',
                    padding: '0.5rem 0.65rem',
                    borderRadius: '4px',
                    border: '1px solid var(--border-subtle)',
                    whiteSpace: 'pre-wrap'
                  }}
                >
                  "{activeObs.source_snippet || 'Document text excerpted during observation parsing.'}"
                </div>
              </div>

              {/* Audit Trail & History Log */}
              {((activeObs.audit_trail && activeObs.audit_trail.length > 0) || activeObs.original_extracted_value != null) && (
                <div
                  style={{
                    padding: '0.75rem 0.85rem',
                    backgroundColor: 'var(--status-neutral-bg)',
                    borderRadius: '6px',
                    border: '1px solid var(--status-neutral-border)'
                  }}
                >
                  <strong className="small" style={{ color: 'var(--text-primary)', display: 'block', marginBottom: '0.4rem' }}>
                    Audit History & Provenance Log:
                  </strong>
                  {activeObs.original_extracted_value != null && (
                    <div className="small muted" style={{ marginBottom: '0.35rem' }}>
                      Original Extracted Value: <strong>{activeObs.original_extracted_value} {activeObs.unit}</strong>
                    </div>
                  )}
                  {activeObs.audit_trail && activeObs.audit_trail.map((entry, idx) => (
                    <div
                      key={idx}
                      className="small"
                      style={{
                        padding: '0.35rem 0',
                        borderTop: idx > 0 ? '1px dashed var(--border-subtle)' : 'none',
                        color: 'var(--text-secondary)'
                      }}
                    >
                      <span style={{ fontWeight: 600, color: 'var(--text-primary)' }}>
                        {entry.action.toUpperCase()}
                      </span>{' '}
                      by <code>{entry.change_source || 'user_verified'}</code> at {entry.changed_at ? entry.changed_at.slice(0, 19).replace('T', ' ') : 'time unrecorded'}:
                      {entry.corrected_value != null && ` Corrected to ${entry.corrected_value}.`}
                      {entry.notes && ` Note: "${entry.notes}"`}
                    </div>
                  ))}
                </div>
              )}

              {/* Action Buttons Bar */}
              <div
                style={{
                  display: 'flex',
                  gap: '0.5rem',
                  flexWrap: 'wrap',
                  paddingTop: '0.75rem',
                  borderTop: '1px solid var(--border-color)'
                }}
              >
                {/* Verify Action */}
                <button
                  type="button"
                  className="primary-btn btn-sm"
                  onClick={() => handleVerify(selectedKey, activeObs)}
                  disabled={loading}
                  style={{ display: 'inline-flex', alignItems: 'center', gap: '0.35rem' }}
                >
                  <IconCheckCircle size={15} /> Verify Correct
                </button>

                {/* Edit Action */}
                <button
                  type="button"
                  className="secondary-btn btn-sm"
                  onClick={() => openEditModal(selectedKey, activeObs)}
                  disabled={loading}
                >
                  Edit Observation
                </button>

                {/* Mark Incorrect Action */}
                <button
                  type="button"
                  className="secondary-btn btn-sm"
                  onClick={() => setIsMarkingIncorrect(true)}
                  disabled={loading}
                  style={{ color: 'var(--status-danger)', borderColor: 'var(--status-danger-border)' }}
                >
                  Mark Incorrect
                </button>

                {/* Remove Action */}
                <button
                  type="button"
                  className="secondary-btn btn-sm"
                  onClick={() => setIsConfirmingRemove(true)}
                  disabled={loading}
                  style={{ color: 'var(--text-muted)' }}
                >
                  Remove
                </button>
              </div>
            </div>
          ) : (
            <div className="card" style={{ padding: '3rem', textAlign: 'center', color: 'var(--text-muted)' }}>
              Select an observation above to view detailed audit provenance.
            </div>
          )}
        </div>
      </div>

      {/* MODAL 1: EDIT OBSERVATION MODAL */}
      {isEditing && (
        <div
          className="modal-backdrop"
          onClick={() => setIsEditing(false)}
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
            className="modal-content"
            onClick={(e) => e.stopPropagation()}
            style={{
              backgroundColor: 'var(--bg-surface)',
              borderRadius: '8px',
              maxWidth: '520px',
              width: '100%',
              padding: '1.5rem',
              boxShadow: 'var(--shadow-lg)'
            }}
          >
            <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: '1rem' }}>
              <h3 style={{ margin: 0, fontSize: '18px' }}>
                Edit Observation: {selectedKey?.toUpperCase()}
              </h3>
              <button
                type="button"
                className="btn-link"
                onClick={() => setIsEditing(false)}
                style={{ background: 'none', border: 'none', cursor: 'pointer', padding: '0.25rem' }}
              >
                <IconClose size={20} />
              </button>
            </div>

            <div
              style={{
                marginBottom: '1rem',
                padding: '0.5rem 0.75rem',
                backgroundColor: 'var(--status-info-bg)',
                borderRadius: '6px',
                fontSize: '12.5px',
                color: 'var(--brand-primary)',
                border: '1px solid var(--status-info-border)'
              }}
            >
              <strong>Audit Safety:</strong> Edits never destroy original extractions. The original value (<code>{activeObs?.value}</code>) will be permanently preserved in the audit log.
            </div>

            <div className="stack gap-sm">
              <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: '0.75rem' }}>
                <div>
                  <label>Measured Value *</label>
                  <input
                    type="number"
                    step="0.01"
                    value={editForm.value}
                    onChange={(e) => setEditForm({ ...editForm, value: e.target.value })}
                    required
                  />
                </div>
                <div>
                  <label>Unit</label>
                  <input
                    type="text"
                    value={editForm.unit}
                    onChange={(e) => setEditForm({ ...editForm, unit: e.target.value })}
                    placeholder="e.g. g/dL, mg/dL"
                  />
                </div>
              </div>

              <div>
                <label>Source Reference Range Raw</label>
                <input
                  type="text"
                  value={editForm.reference_range_raw}
                  onChange={(e) => setEditForm({ ...editForm, reference_range_raw: e.target.value })}
                  placeholder="e.g. 12.0 - 16.0 g/dL"
                />
              </div>

              <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: '0.75rem' }}>
                <div>
                  <label>Parsed Lower Bound (Min)</label>
                  <input
                    type="number"
                    step="0.01"
                    value={editForm.parsed_min}
                    onChange={(e) => setEditForm({ ...editForm, parsed_min: e.target.value })}
                    placeholder="Optional min"
                  />
                </div>
                <div>
                  <label>Parsed Upper Bound (Max)</label>
                  <input
                    type="number"
                    step="0.01"
                    value={editForm.parsed_max}
                    onChange={(e) => setEditForm({ ...editForm, parsed_max: e.target.value })}
                    placeholder="Optional max"
                  />
                </div>
              </div>

              <div>
                <label>Clinician Rationale / Audit Notes *</label>
                <textarea
                  rows={3}
                  value={editForm.notes}
                  onChange={(e) => setEditForm({ ...editForm, notes: e.target.value })}
                  placeholder="Explain why this value or range was corrected..."
                  required
                />
              </div>
            </div>

            <div style={{ display: 'flex', justifyContent: 'flex-end', gap: '0.5rem', marginTop: '1.25rem' }}>
              <button type="button" className="secondary-btn" onClick={() => setIsEditing(false)}>
                Cancel
              </button>
              <button type="button" className="primary-btn" onClick={handleSaveEdit}>
                Save & Mark User-Verified
              </button>
            </div>
          </div>
        </div>
      )}

      {/* MODAL 2: MARK INCORRECT MODAL */}
      {isMarkingIncorrect && (
        <div
          className="modal-backdrop"
          onClick={() => setIsMarkingIncorrect(false)}
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
            className="modal-content"
            onClick={(e) => e.stopPropagation()}
            style={{
              backgroundColor: 'var(--bg-surface)',
              borderRadius: '8px',
              maxWidth: '480px',
              width: '100%',
              padding: '1.5rem',
              boxShadow: 'var(--shadow-lg)'
            }}
          >
            <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: '1rem' }}>
              <h3 style={{ margin: 0, fontSize: '18px', color: 'var(--status-danger)' }}>
                Mark Observation Incorrect
              </h3>
              <button
                type="button"
                className="btn-link"
                onClick={() => setIsMarkingIncorrect(false)}
                style={{ background: 'none', border: 'none', cursor: 'pointer', padding: '0.25rem' }}
              >
                <IconClose size={20} />
              </button>
            </div>

            <p className="small muted" style={{ marginTop: 0 }}>
              Flag <strong>{selectedKey?.toUpperCase()}</strong> as an erroneous extraction (e.g. false positive OCR match, header misidentified as lab test).
            </p>

            <div className="stack gap-sm">
              <label>Reason for Flagging *</label>
              <textarea
                rows={3}
                value={markIncorrectNotes}
                onChange={(e) => setMarkIncorrectNotes(e.target.value)}
                placeholder="e.g. Test name was parsed from unrelated footer text..."
                required
              />
            </div>

            <div style={{ display: 'flex', justifyContent: 'flex-end', gap: '0.5rem', marginTop: '1.25rem' }}>
              <button type="button" className="secondary-btn" onClick={() => setIsMarkingIncorrect(false)}>
                Cancel
              </button>
              <button
                type="button"
                className="primary-btn"
                onClick={handleConfirmMarkIncorrect}
                style={{ backgroundColor: 'var(--status-danger)', borderColor: 'var(--status-danger)' }}
              >
                Confirm Mark Incorrect
              </button>
            </div>
          </div>
        </div>
      )}

      {/* MODAL 3: CONFIRM REMOVE OBSERVATION */}
      {isConfirmingRemove && (
        <div
          className="modal-backdrop"
          onClick={() => setIsConfirmingRemove(false)}
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
            className="modal-content"
            onClick={(e) => e.stopPropagation()}
            style={{
              backgroundColor: 'var(--bg-surface)',
              borderRadius: '8px',
              maxWidth: '440px',
              width: '100%',
              padding: '1.5rem',
              boxShadow: 'var(--shadow-lg)'
            }}
          >
            <h3 style={{ margin: 0, fontSize: '18px' }}>Remove Observation</h3>
            <p className="small muted" style={{ marginTop: '0.5rem' }}>
              Are you sure you want to remove <strong>{selectedKey?.toUpperCase()}</strong> from this report's observation record?
            </p>

            <div style={{ display: 'flex', justifyContent: 'flex-end', gap: '0.5rem', marginTop: '1.25rem' }}>
              <button type="button" className="secondary-btn" onClick={() => setIsConfirmingRemove(false)}>
                Cancel
              </button>
              <button
                type="button"
                className="primary-btn"
                onClick={handleConfirmRemove}
                style={{ backgroundColor: 'var(--status-danger)', borderColor: 'var(--status-danger)' }}
              >
                Yes, Remove Observation
              </button>
            </div>
          </div>
        </div>
      )}

      {/* MODAL 4: ADD MISSING OBSERVATION */}
      {isAddingMissing && (
        <div
          className="modal-backdrop"
          onClick={() => setIsAddingMissing(false)}
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
            className="modal-content"
            onClick={(e) => e.stopPropagation()}
            style={{
              backgroundColor: 'var(--bg-surface)',
              borderRadius: '8px',
              maxWidth: '540px',
              width: '100%',
              padding: '1.5rem',
              boxShadow: 'var(--shadow-lg)'
            }}
          >
            <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: '1rem' }}>
              <h3 style={{ margin: 0, fontSize: '18px' }}>Add Missing Observation</h3>
              <button
                type="button"
                className="btn-link"
                onClick={() => setIsAddingMissing(false)}
                style={{ background: 'none', border: 'none', cursor: 'pointer', padding: '0.25rem' }}
              >
                <IconClose size={20} />
              </button>
            </div>

            <p className="small muted" style={{ marginTop: 0 }}>
              Manually add a laboratory observation found in the source document that was missed during automated extraction.
            </p>

            <div className="stack gap-sm">
              <div style={{ display: 'grid', gridTemplateColumns: '2fr 1fr', gap: '0.75rem' }}>
                <div>
                  <label>Test / Observation Name *</label>
                  <input
                    type="text"
                    value={addForm.test_name}
                    onChange={(e) => setAddForm({ ...addForm, test_name: e.target.value })}
                    placeholder="e.g. Ferritin, Troponin I"
                    required
                  />
                </div>
                <div>
                  <label>Measured Value *</label>
                  <input
                    type="number"
                    step="0.01"
                    value={addForm.value}
                    onChange={(e) => setAddForm({ ...addForm, value: e.target.value })}
                    placeholder="e.g. 45.2"
                    required
                  />
                </div>
              </div>

              <div style={{ display: 'grid', gridTemplateColumns: '1fr 2fr', gap: '0.75rem' }}>
                <div>
                  <label>Unit</label>
                  <input
                    type="text"
                    value={addForm.unit}
                    onChange={(e) => setAddForm({ ...addForm, unit: e.target.value })}
                    placeholder="e.g. ng/mL"
                  />
                </div>
                <div>
                  <label>Source Reference Range Raw</label>
                  <input
                    type="text"
                    value={addForm.reference_range_raw}
                    onChange={(e) => setAddForm({ ...addForm, reference_range_raw: e.target.value })}
                    placeholder="e.g. 30.0 - 400.0 ng/mL"
                  />
                </div>
              </div>

              <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr 1fr', gap: '0.75rem' }}>
                <div>
                  <label>Parsed Min</label>
                  <input
                    type="number"
                    step="0.01"
                    value={addForm.parsed_min}
                    onChange={(e) => setAddForm({ ...addForm, parsed_min: e.target.value })}
                    placeholder="Min bound"
                  />
                </div>
                <div>
                  <label>Parsed Max</label>
                  <input
                    type="number"
                    step="0.01"
                    value={addForm.parsed_max}
                    onChange={(e) => setAddForm({ ...addForm, parsed_max: e.target.value })}
                    placeholder="Max bound"
                  />
                </div>
                <div>
                  <label>Source Page</label>
                  <input
                    type="number"
                    value={addForm.source_page}
                    onChange={(e) => setAddForm({ ...addForm, source_page: e.target.value })}
                    placeholder="1"
                  />
                </div>
              </div>

              <div>
                <label>Source Report Snippet / Context</label>
                <textarea
                  rows={2}
                  value={addForm.source_snippet}
                  onChange={(e) => setAddForm({ ...addForm, source_snippet: e.target.value })}
                  placeholder="Paste or cite the surrounding line from the source document..."
                />
              </div>

              <div>
                <label>Clinician Notes</label>
                <input
                  type="text"
                  value={addForm.notes}
                  onChange={(e) => setAddForm({ ...addForm, notes: e.target.value })}
                  placeholder="e.g. Found on page 2 table 3"
                />
              </div>
            </div>

            <div style={{ display: 'flex', justifyContent: 'flex-end', gap: '0.5rem', marginTop: '1.25rem' }}>
              <button type="button" className="secondary-btn" onClick={() => setIsAddingMissing(false)}>
                Cancel
              </button>
              <button type="button" className="primary-btn" onClick={handleSaveAddMissing}>
                Save Observation
              </button>
            </div>
          </div>
        </div>
      )}
    </div>
  )
}
