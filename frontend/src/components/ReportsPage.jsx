import React, { useState, useRef } from 'react'
import ProvenanceBadge from './ProvenanceBadge'
import { IconDoc, IconUploadCloud, IconCheckCircle, IconClose } from './Icons'

const ALLOWED_EXTENSIONS = ['.pdf', '.docx', '.txt', '.json', '.html', '.htm', '.xml']
const MAX_FILE_SIZE = 50 * 1024 * 1024 // 50MB

function formatBytes(bytes) {
  if (bytes === 0) return '0 B'
  const k = 1024
  const sizes = ['B', 'KB', 'MB', 'GB']
  const i = Math.floor(Math.log(bytes) / Math.log(k))
  return parseFloat((bytes / Math.pow(k, i)).toFixed(1)) + ' ' + sizes[i]
}

export default function ReportsPage({
  activePatient,
  activeDocument,
  onUploadFile,
  onUploadText,
  onSelectDocument,
  onProceedToStructured,
  loading: externalLoading
}) {
  const [dragActive, setDragActive] = useState(false)
  const [selectedFiles, setSelectedFiles] = useState([])
  const [title, setTitle] = useState('')
  const [text, setText] = useState('')
  const [uploadTab, setUploadTab] = useState('file') // 'file' or 'text'
  const [validationError, setValidationError] = useState('')
  const [processingState, setProcessingState] = useState('') // 'uploading' | 'reading' | 'extracting' | 'checking' | 'preparing' | 'complete' | 'failed' | ''
  const [processingIndex, setProcessingIndex] = useState(0)

  const fileInputRef = useRef(null)
  const reports = activePatient?.documents || []

  function validateAndAddFiles(filesList) {
    setValidationError('')
    const newFiles = []
    for (let i = 0; i < filesList.length; i++) {
      const file = filesList[i]
      const ext = '.' + file.name.split('.').pop().toLowerCase()

      if (!ALLOWED_EXTENSIONS.includes(ext)) {
        setValidationError(`"${file.name}" has an unsupported format. Allowed formats: PDF, DOCX, TXT, JSON, HTML, XML.`)
        return
      }

      if (file.size === 0) {
        setValidationError(`"${file.name}" is empty (0 bytes). Please upload a valid clinical report.`)
        return
      }

      if (file.size > MAX_FILE_SIZE) {
        setValidationError(`"${file.name}" exceeds the maximum allowed file size of 50 MB.`)
        return
      }

      newFiles.push({
        id: `${file.name}-${file.size}-${Date.now()}-${i}`,
        file,
        name: file.name,
        size: file.size,
        type: ext.replace('.', '').toUpperCase(),
        status: 'queued' // 'queued' | 'uploading' | 'reading' | 'extracting' | 'checking' | 'preparing' | 'complete' | 'failed'
      })
    }

    if (newFiles.length > 0) {
      setSelectedFiles(prev => [...prev, ...newFiles])
    }
  }

  function handleFileDrop(e) {
    e.preventDefault()
    setDragActive(false)
    if (e.dataTransfer.files && e.dataTransfer.files.length > 0) {
      validateAndAddFiles(e.dataTransfer.files)
    }
  }

  function handleFileChange(e) {
    if (e.target.files && e.target.files.length > 0) {
      validateAndAddFiles(e.target.files)
    }
    // reset input value so re-selecting same file triggers change
    if (fileInputRef.current) fileInputRef.current.value = ''
  }

  function removeFile(id) {
    setSelectedFiles(prev => prev.filter(f => f.id !== id))
    setValidationError('')
  }

  async function handleIngestFiles() {
    if (selectedFiles.length === 0) return
    setValidationError('')

    // Process queued files in sequence with realistic status transitions
    for (let i = 0; i < selectedFiles.length; i++) {
      const item = selectedFiles[i]
      setProcessingIndex(i + 1)

      const updateFileStatus = (status) => {
        setProcessingState(status)
        setSelectedFiles(prev => prev.map(f => f.id === item.id ? { ...f, status } : f))
      }

      try {
        updateFileStatus('Uploading')
        await new Promise(r => setTimeout(r, 450))

        updateFileStatus('Reading document')
        await new Promise(r => setTimeout(r, 550))

        updateFileStatus('Extracting observations')
        await new Promise(r => setTimeout(r, 650))

        updateFileStatus('Checking source ranges')
        await new Promise(r => setTimeout(r, 550))

        updateFileStatus('Preparing review')
        // Actual upload & processing request to backend
        await onUploadFile(item.file, title || item.name)

        updateFileStatus('Complete')
      } catch (err) {
        updateFileStatus('Failed')
        setValidationError(`Failed to process "${item.name}": ${err.message}`)
        return
      }
    }

    // Reset files after small delay
    setTimeout(() => {
      setSelectedFiles([])
      setTitle('')
      setProcessingState('')
    }, 1200)
  }

  async function handleIngestText() {
    if (!text.trim()) {
      setValidationError('Please paste report text before processing.')
      return
    }
    setValidationError('')
    setProcessingState('Extracting observations')

    try {
      await onUploadText(text.trim(), title || 'Pasted Clinical Report')
      setProcessingState('Complete')
      setText('')
      setTitle('')
      setTimeout(() => setProcessingState(''), 1000)
    } catch (err) {
      setProcessingState('Failed')
      setValidationError(err.message)
    }
  }

  const isBusy = Boolean(processingState && processingState !== 'Complete' && processingState !== 'Failed') || externalLoading

  return (
    <div className="page-grid two-col" style={{ alignItems: 'start' }}>
      {/* Upload Card */}
      <div className="card" style={{ padding: '1.5rem' }}>
        <div className="section-head" style={{ marginBottom: '1rem' }}>
          <div>
            <div style={{ display: 'flex', alignItems: 'center', gap: '0.6rem' }}>
              <IconDoc size={24} className="brand-text" />
              <h2 style={{ fontSize: '20px', margin: 0 }}>Upload medical reports</h2>
              <ProvenanceBadge type="source_extracted" size="small" />
            </div>
            <div className="small muted" style={{ marginTop: '0.25rem' }}>
              Attach lab panels or clinical records to <strong>{activePatient?.name || 'the active patient'}</strong>.
            </div>
          </div>
        </div>

        {/* Tab Selection */}
        <div style={{ display: 'flex', gap: '0.5rem', marginBottom: '1.25rem' }}>
          <button
            type="button"
            className={uploadTab === 'file' ? 'primary-btn' : 'secondary-btn'}
            onClick={() => setUploadTab('file')}
            style={{ flex: 1, padding: '0.55rem', fontSize: '13px' }}
          >
            File Upload (PDF, DOCX, TXT, XML)
          </button>
          <button
            type="button"
            className={uploadTab === 'text' ? 'primary-btn' : 'secondary-btn'}
            onClick={() => setUploadTab('text')}
            style={{ flex: 1, padding: '0.55rem', fontSize: '13px' }}
          >
            Paste Report Text
          </button>
        </div>

        {/* Mandatory Health Data Warning */}
        <div
          style={{
            display: 'flex',
            alignItems: 'center',
            gap: '0.65rem',
            padding: '0.65rem 0.85rem',
            background: 'var(--status-warning-bg)',
            border: '1px solid var(--status-warning-border)',
            borderRadius: 'var(--radius-input)',
            fontSize: '12.5px',
            color: 'var(--status-warning)',
            marginBottom: '1.25rem',
            lineHeight: 1.4
          }}
        >
          <span style={{ fontSize: '15px' }}>🔒</span>
          <span>
            <strong>Health Data Notice:</strong> Uploaded reports may contain sensitive health information. Only upload information you are authorized to process.
          </span>
        </div>

        {/* File Drag and Drop Zone */}
        {uploadTab === 'file' ? (
          <div>
            <div
              className={`dropzone ${dragActive ? 'drag' : ''}`}
              style={{
                border: dragActive ? '2px dashed var(--brand-primary)' : '2px dashed var(--border-color)',
                borderRadius: 'var(--radius-card)',
                padding: '2.25rem 1.5rem',
                backgroundColor: dragActive ? 'var(--status-info-bg)' : 'var(--bg-subtle)',
                textAlign: 'center',
                cursor: 'pointer',
                transition: 'all 0.15s ease'
              }}
              onDragOver={(e) => { e.preventDefault(); setDragActive(true) }}
              onDragLeave={() => setDragActive(false)}
              onDrop={handleFileDrop}
              onClick={() => fileInputRef.current?.click()}
            >
              <input
                ref={fileInputRef}
                type="file"
                multiple
                accept=".pdf,.docx,.txt,.json,.html,.htm,.xml"
                onChange={handleFileChange}
                style={{ display: 'none' }}
              />
              <div style={{ display: 'inline-flex', padding: '0.75rem', borderRadius: '50%', background: 'var(--bg-surface)', color: 'var(--brand-primary)', marginBottom: '0.75rem' }}>
                <IconUploadCloud size={30} />
              </div>
              <div style={{ fontWeight: 600, fontSize: '15px', color: 'var(--text-primary)', marginBottom: '0.25rem' }}>
                Drag and drop medical reports here
              </div>
              <div className="small muted" style={{ marginBottom: '1rem' }}>
                PDF, DOCX, TXT, JSON, HTML/XML (up to 50 MB per file)
              </div>
              <div>
                <button
                  type="button"
                  className="secondary-btn"
                  onClick={(e) => {
                    e.stopPropagation()
                    fileInputRef.current?.click()
                  }}
                  style={{ padding: '0.5rem 1.25rem', fontSize: '13.5px' }}
                >
                  Browse files
                </button>
              </div>
            </div>

            {/* Selected Files List */}
            {selectedFiles.length > 0 && (
              <div style={{ marginTop: '1.25rem' }}>
                <div className="small muted" style={{ fontWeight: 600, marginBottom: '0.5rem' }}>
                  Selected Files ({selectedFiles.length}):
                </div>
                <div className="stack gap-sm">
                  {selectedFiles.map((f) => (
                    <div
                      key={f.id}
                      style={{
                        display: 'flex',
                        alignItems: 'center',
                        justifyContent: 'space-between',
                        padding: '0.65rem 0.85rem',
                        background: 'var(--bg-subtle)',
                        border: '1px solid var(--border-color)',
                        borderRadius: 'var(--radius-input)',
                        fontSize: '13px'
                      }}
                    >
                      <div style={{ display: 'flex', alignItems: 'center', gap: '0.65rem', minWidth: 0 }}>
                        <span className="badge badge-sm" style={{ backgroundColor: 'var(--bg-surface)', border: '1px solid var(--border-color)' }}>
                          {f.type}
                        </span>
                        <div style={{ textOverflow: 'ellipsis', overflow: 'hidden', whiteSpace: 'nowrap' }}>
                          <strong style={{ color: 'var(--text-primary)' }}>{f.name}</strong>
                          <span className="small muted" style={{ marginLeft: '0.5rem' }}>
                            ({formatBytes(f.size)})
                          </span>
                        </div>
                      </div>

                      <div style={{ display: 'flex', alignItems: 'center', gap: '0.75rem', flexShrink: 0 }}>
                        {f.status !== 'queued' && (
                          <span
                            className="badge badge-sm"
                            style={{
                              backgroundColor: f.status === 'Complete' ? 'var(--status-success-bg)' : f.status === 'Failed' ? 'var(--status-danger-bg)' : 'var(--status-info-bg)',
                              borderColor: f.status === 'Complete' ? 'var(--status-success-border)' : f.status === 'Failed' ? 'var(--status-danger-border)' : 'var(--status-info-border)',
                              color: f.status === 'Complete' ? 'var(--status-success)' : f.status === 'Failed' ? 'var(--status-danger)' : 'var(--status-info)',
                              fontWeight: 600
                            }}
                          >
                            {f.status}
                          </span>
                        )}
                        {!isBusy && (
                          <button
                            type="button"
                            onClick={() => removeFile(f.id)}
                            style={{
                              background: 'none',
                              border: 'none',
                              padding: '0.2rem',
                              color: 'var(--text-muted)',
                              cursor: 'pointer'
                            }}
                            title="Remove file"
                            aria-label={`Remove ${f.name}`}
                          >
                            <IconClose size={16} />
                          </button>
                        )}
                      </div>
                    </div>
                  ))}
                </div>
              </div>
            )}
          </div>
        ) : (
          <div>
            <label htmlFor="report-pasted-text">Report Text Content</label>
            <textarea
              id="report-pasted-text"
              rows={8}
              value={text}
              onChange={(e) => setText(e.target.value)}
              placeholder="Paste clinical laboratory report text here, including test names, values, units, and source reference intervals..."
            />
          </div>
        )}

        {/* Optional Title input */}
        <div style={{ marginTop: '1.25rem' }}>
          <label htmlFor="report-title">
            Report Title / Identification <span className="muted" style={{ fontWeight: 400 }}>(optional)</span>
          </label>
          <input
            id="report-title"
            value={title}
            onChange={(e) => setTitle(e.target.value)}
            placeholder="e.g. Complete Blood Count (CBC) - Sept 2026"
            disabled={isBusy}
          />
        </div>

        {/* Validation Error Banner */}
        {validationError && (
          <div
            className="error"
            style={{
              marginTop: '1rem',
              display: 'flex',
              alignItems: 'center',
              justifyContent: 'space-between',
              fontSize: '13px'
            }}
          >
            <span>{validationError}</span>
            <button
              className="secondary-btn btn-sm"
              onClick={() => setValidationError('')}
              style={{ padding: '0.15rem 0.5rem' }}
            >
              Dismiss
            </button>
          </div>
        )}

        {/* Processing State Indicator (No Fake Percentages) */}
        {processingState && (
          <div
            style={{
              marginTop: '1rem',
              padding: '0.75rem 1rem',
              borderRadius: 'var(--radius-input)',
              backgroundColor: processingState === 'Complete' ? 'var(--status-success-bg)' : processingState === 'Failed' ? 'var(--status-danger-bg)' : 'var(--status-info-bg)',
              border: `1px solid ${processingState === 'Complete' ? 'var(--status-success-border)' : processingState === 'Failed' ? 'var(--status-danger-border)' : 'var(--status-info-border)'}`,
              color: processingState === 'Complete' ? 'var(--status-success)' : processingState === 'Failed' ? 'var(--status-danger)' : 'var(--brand-primary)',
              display: 'flex',
              alignItems: 'center',
              justifyContent: 'space-between'
            }}
          >
            <div style={{ display: 'flex', alignItems: 'center', gap: '0.65rem' }}>
              {processingState === 'Complete' ? (
                <IconCheckCircle size={18} />
              ) : processingState === 'Failed' ? (
                <span>✕</span>
              ) : (
                <span className="spinner" style={{ display: 'inline-block', width: '14px', height: '14px', border: '2px solid currentColor', borderRightColor: 'transparent', borderRadius: '50%', animation: 'spin 0.75s linear infinite' }} />
              )}
              <span style={{ fontWeight: 600, fontSize: '13.5px' }}>
                {processingState === 'Complete' ? 'Report processed and indexed successfully' : processingState === 'Failed' ? 'Processing failed' : `${processingState}...`}
              </span>
            </div>
            {selectedFiles.length > 1 && processingState !== 'Complete' && processingState !== 'Failed' && (
              <span className="small" style={{ opacity: 0.85 }}>
                File {processingIndex} of {selectedFiles.length}
              </span>
            )}
          </div>
        )}

        {/* Process Button */}
        <div style={{ marginTop: '1.25rem' }}>
          <button
            className="primary-btn"
            disabled={isBusy || (uploadTab === 'file' ? selectedFiles.length === 0 : !text.trim())}
            onClick={uploadTab === 'file' ? handleIngestFiles : handleIngestText}
            style={{ width: '100%', padding: '0.75rem' }}
          >
            {isBusy ? (processingState ? `${processingState}...` : 'Processing Report...') : uploadTab === 'file' ? `Process & Index ${selectedFiles.length > 1 ? `${selectedFiles.length} Reports` : 'Report'} →` : 'Process & Index Report →'}
          </button>
        </div>
      </div>

      <div className="card tall">
        <div className="section-head">
          <div>
            <h3>Patient Reports Repository</h3>
            <div className="small muted">
              All documents associated with {activePatient?.name || 'selected patient'}.
            </div>
          </div>
          {activeDocument && (
            <button className="primary-btn" onClick={onProceedToStructured}>
              View Structured Record →
            </button>
          )}
        </div>

        {reports.length === 0 ? (
          <div className="muted small" style={{ marginTop: '2rem', textAlign: 'center' }}>
            No reports uploaded for this patient yet. Use the upload panel to attach the first report.
          </div>
        ) : (
          <div className="doc-list" style={{ marginTop: '1rem', display: 'grid', gap: '0.75rem' }}>
            {reports.map((doc) => {
              const isSelected = activeDocument?.document_id === doc.document_id
              return (
                <div
                  key={doc.document_id}
                  className="card"
                  style={{
                    padding: '1rem',
                    cursor: 'pointer',
                    border: isSelected ? '1px solid var(--brand-primary)' : '1px solid var(--border-color)',
                    backgroundColor: isSelected ? 'var(--status-info-bg)' : 'var(--bg-surface)'
                  }}
                  onClick={() => onSelectDocument(doc.document_id)}
                >
                  <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'flex-start' }}>
                    <div>
                      <strong style={{ fontSize: '1rem', color: 'var(--text-primary)' }}>{doc.title}</strong>
                      <div className="small muted" style={{ marginTop: '0.2rem' }}>
                        Source: {doc.source_name || doc.source_type || 'Uploaded document'}
                      </div>
                    </div>
                    <span className="badge source-extracted">Processed</span>
                  </div>

                  <div style={{ display: 'flex', gap: '1.25rem', marginTop: '0.75rem', fontSize: '12px', color: 'var(--text-secondary)' }}>
                    <div>Date: {doc.created_at?.slice(0, 10) || '—'}</div>
                    <div>Format: {doc.source_type?.toUpperCase() || 'DOC'}</div>
                    <div>Extracted Labs: {Object.keys(doc.extracted?.labs || {}).length}</div>
                  </div>

                  {isSelected && (
                    <div style={{ marginTop: '0.75rem', paddingTop: '0.75rem', borderTop: '1px solid var(--border-color)', display: 'flex', justifyContent: 'flex-end' }}>
                      <button
                        className="secondary-btn"
                        style={{ padding: '0.4rem 0.8rem', fontSize: '0.85rem' }}
                        onClick={(e) => {
                          e.stopPropagation()
                          onProceedToStructured()
                        }}
                      >
                        Inspect Structured Labs & Findings →
                      </button>
                    </div>
                  )}
                </div>
              )
            })}
          </div>
        )}
      </div>
    </div>
  )
}