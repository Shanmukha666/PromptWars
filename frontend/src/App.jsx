import React, { useEffect, useState } from 'react'
import Sidebar from './components/Sidebar'
import TopBar from './components/TopBar'
import Breadcrumbs from './components/Breadcrumbs'
import HelpModal from './components/HelpModal'
import SettingsModal from './components/SettingsModal'
import OverviewPage from './components/OverviewPage'
import PatientProfilePage from './components/PatientProfilePage'
import ReportsPage from './components/ReportsPage'
import StructuredRecordPage from './components/StructuredRecordPage'
import ReviewVerificationPage from './components/ReviewVerificationPage'
import TimelineHistoryPage from './components/TimelineHistoryPage'
import ProcessingEvidencePage from './components/ProcessingEvidencePage'
import { DEMO_DATA } from './demoData'

const API_BASE = import.meta.env.VITE_API_BASE_URL || 'http://localhost:8000'

async function request(path, options = {}) {
  const res = await fetch(`${API_BASE}${path}`, options)
  if (!res.ok) {
    const text = await res.text()
    throw new Error(text || `Request failed: ${res.status}`)
  }
  return res.json()
}

export default function App() {
  // 6-stage clinical workflow state: overview | profile | reports | structured | review | timeline
  const [stage, setStage] = useState('overview')
  const [health, setHealth] = useState(null)
  const [documents, setDocuments] = useState([])
  const [patients, setPatients] = useState([])
  const [activePatient, setActivePatient] = useState(null)
  const [activeDocument, setActiveDocument] = useState(null)
  const [loading, setLoading] = useState(false)
  const [error, setError] = useState('')

  // Modals & Mobile Shell State
  const [isHelpOpen, setIsHelpOpen] = useState(false)
  const [isSettingsOpen, setIsSettingsOpen] = useState(false)
  const [isMobileSidebarOpen, setIsMobileSidebarOpen] = useState(false)
  const [isDemoMode, setIsDemoMode] = useState(false)
  const [dismissDemoBanner, setDismissDemoBanner] = useState(false)

  useEffect(() => {
    refreshAll()
  }, [])

  async function refreshAll() {
    try {
      const [healthData, docsData, patientsData] = await Promise.all([
        request('/api/health'),
        request('/api/documents'),
        request('/api/patients')
      ])
      setHealth(healthData)
      setDocuments(docsData.items || [])
      setPatients(patientsData.items || [])
      setIsDemoMode(false)
      if (activePatient?.patient_id) {
        await openPatient(activePatient.patient_id, false)
      }
    } catch (err) {
      console.warn('Backend API connection failed, initializing browser preview demo mode:', err)
      setIsDemoMode(true)
      setHealth(DEMO_DATA.health)
      setPatients(DEMO_DATA.patients)
      const allDocs = DEMO_DATA.patients.flatMap(p => p.documents || [])
      setDocuments(allDocs)
      if (!activePatient && DEMO_DATA.patients.length > 0) {
        const firstPat = DEMO_DATA.patients[0]
        setActivePatient(firstPat)
        if (firstPat.documents?.length > 0) {
          setActiveDocument(firstPat.documents[0])
        }
      }
    }
  }

  async function openPatient(patientId, navigateToProfile = true) {
    setLoading(true)
    setError('')
    try {
      if (isDemoMode) {
        const found = patients.find(p => p.patient_id === patientId) || DEMO_DATA.patients[0]
        setActivePatient(found)
        if (found?.documents?.length > 0) {
          setActiveDocument(found.documents[0])
        } else {
          setActiveDocument(null)
        }
        if (navigateToProfile) {
          setStage('profile')
        }
        return
      }
      const data = await request(`/api/patients/${patientId}`)
      setActivePatient(data)
      if (data.documents && data.documents.length > 0) {
        await openDocument(data.documents[0].document_id)
      } else {
        setActiveDocument(null)
      }
      if (navigateToProfile) {
        setStage('profile')
      }
    } catch (err) {
      setError(err.message)
    } finally {
      setLoading(false)
    }
  }

  async function openDocument(documentId) {
    setLoading(true)
    setError('')
    try {
      if (isDemoMode) {
        const doc = documents.find(d => d.document_id === documentId) || 
                    activePatient?.documents?.find(d => d.document_id === documentId) ||
                    DEMO_DATA.patients[0].documents[0]
        setActiveDocument(doc)
        return
      }
      const data = await request(`/api/documents/${documentId}`)
      setActiveDocument(data)
    } catch (err) {
      setError(err.message)
    } finally {
      setLoading(false)
    }
  }

  async function handleSavePatient(payload) {
    setLoading(true)
    setError('')
    try {
      if (activePatient?.patient_id) {
        await request(`/api/patients/${activePatient.patient_id}`, {
          method: 'PUT',
          headers: { 'Content-Type': 'application/json' },
          body: JSON.stringify(payload)
        })
        await openPatient(activePatient.patient_id, false)
      } else {
        const res = await request('/api/patients', {
          method: 'POST',
          headers: { 'Content-Type': 'application/json' },
          body: JSON.stringify(payload)
        })
        await refreshAll()
        await openPatient(res.patient_id, true)
      }
    } catch (err) {
      setError(err.message)
    } finally {
      setLoading(false)
    }
  }

  async function handleUploadFile(file, title) {
    if (!file) return
    setLoading(true)
    setError('')
    try {
      const body = new FormData()
      body.append('file', file)
      if (title.trim()) body.append('title', title.trim())
      if (activePatient?.patient_id) body.append('patient_id', activePatient.patient_id)
      const data = await request('/api/ingest/file', { method: 'POST', body })
      await refreshAll()
      await openDocument(data.document_id)
      setStage('structured')
    } catch (err) {
      setError(err.message)
    } finally {
      setLoading(false)
    }
  }

  async function handleUploadText(text, title) {
    if (!text.trim()) return
    setLoading(true)
    setError('')
    try {
      const data = await request('/api/ingest/text', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          title: title.trim() || 'Clinical Report Text',
          text,
          patient_id: activePatient?.patient_id || null
        })
      })
      await refreshAll()
      await openDocument(data.document_id)
      setStage('structured')
    } catch (err) {
      setError(err.message)
    } finally {
      setLoading(false)
    }
  }

  async function handleVerifyOrEditLab(verificationPayload) {
    setLoading(true)
    setError('')
    try {
      if (isDemoMode) {
        if (activeDocument && activeDocument.extracted?.labs) {
          const updatedLabs = { ...activeDocument.extracted.labs }
          const action = verificationPayload.action || 'verify'
          const key = verificationPayload.test_key
          if (action === 'remove') {
            delete updatedLabs[key]
          } else if (action === 'add') {
            updatedLabs[key] = {
              test_name: verificationPayload.test_name || key,
              display_name: (verificationPayload.test_name || key).toUpperCase(),
              value: verificationPayload.value,
              unit: verificationPayload.unit || '',
              reference_range_raw: verificationPayload.reference_range_raw,
              reference_range_low: verificationPayload.reference_range_low,
              reference_range_high: verificationPayload.reference_range_high,
              reference_range_operator: 'between',
              reference_range: verificationPayload.reference_range_low != null ? { min: verificationPayload.reference_range_low, max: verificationPayload.reference_range_high } : null,
              status: verificationPayload.status || 'not_assessed',
              source_snippet: verificationPayload.source_snippet || 'Clinician manual observation',
              verification_status: 'verified',
              provenance_type: 'user_verified'
            }
          } else if (updatedLabs[key]) {
            updatedLabs[key] = {
              ...updatedLabs[key],
              value: verificationPayload.value ?? updatedLabs[key].value,
              unit: verificationPayload.unit ?? updatedLabs[key].unit,
              status: verificationPayload.status ?? updatedLabs[key].status,
              verification_status: action === 'mark_incorrect' ? 'incorrect' : (action === 'edit' ? 'edited' : 'verified'),
              provenance_type: 'user_verified'
            }
          }
          const updatedDoc = {
            ...activeDocument,
            extracted: { ...activeDocument.extracted, labs: updatedLabs }
          }
          setActiveDocument(updatedDoc)
        }
        return
      }
      const res = await request('/api/documents/verify-lab', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify(verificationPayload)
      })
      if (res.document) {
        setActiveDocument(res.document)
      }
      if (activePatient?.patient_id) {
        await openPatient(activePatient.patient_id, false)
      }
    } catch (err) {
      setError(err.message)
    } finally {
      setLoading(false)
    }
  }

  function renderCurrentStage() {
    switch (stage) {
      case 'overview':
        return (
          <OverviewPage
            patients={patients}
            activePatient={activePatient}
            onSelectPatient={(id) => openPatient(id, false)}
            onNewPatient={() => {
              setActivePatient(null)
              setActiveDocument(null)
              setStage('profile')
            }}
            documents={documents}
            health={health}
            onProceedToProfile={() => setStage('profile')}
            onSelectDocument={async (docId) => {
              await openDocument(docId)
              setStage('structured')
            }}
            onNavigateStage={(targetStage) => setStage(targetStage)}
          />
        )
      case 'profile':
        return (
          <PatientProfilePage
            activePatient={activePatient}
            onSavePatient={handleSavePatient}
            onProceedToReports={() => setStage('reports')}
            loading={loading}
          />
        )
      case 'reports':
        return (
          <ReportsPage
            activePatient={activePatient}
            activeDocument={activeDocument}
            onUploadFile={handleUploadFile}
            onUploadText={handleUploadText}
            onSelectDocument={openDocument}
            onProceedToStructured={() => setStage('structured')}
            loading={loading}
          />
        )
      case 'structured':
        return (
          <StructuredRecordPage
            activePatient={activePatient}
            activeDocument={activeDocument}
            onSelectDocument={openDocument}
            onProceedToReview={() => setStage('review')}
            onProceedToTimeline={() => setStage('timeline')}
            onNavigateStage={(targetStage) => setStage(targetStage)}
          />
        )
      case 'review':
        return (
          <ReviewVerificationPage
            activePatient={activePatient}
            activeDocument={activeDocument}
            onSelectDocument={openDocument}
            onVerifyOrEditLab={handleVerifyOrEditLab}
            onProceedToTimeline={() => setStage('timeline')}
            onNavigateStage={(targetStage) => setStage(targetStage)}
            loading={loading}
          />
        )
      case 'timeline':
        return (
          <TimelineHistoryPage
            activePatient={activePatient}
            onSelectDocument={(id) => {
              openDocument(id)
              setStage('structured')
            }}
          />
        )
      case 'processing':
        return (
          <ProcessingEvidencePage
            activePatient={activePatient}
            activeDocument={activeDocument}
            onSelectDocument={openDocument}
            onNavigateStage={(targetStage) => setStage(targetStage)}
            loading={loading}
          />
        )
      default:
        return null
    }
  }

  return (
    <div className="app-shell">
      {/* WCAG 2.4.1 Skip Link */}
      <a href="#main-content" className="skip-link">
        Skip to main content
      </a>
      {/* 240px Left Navigation Sidebar */}
      <Sidebar
        currentStage={stage}
        onSelectStage={(newStage) => setStage(newStage)}
        onOpenSettings={() => setIsSettingsOpen(true)}
        isOpenMobile={isMobileSidebarOpen}
        onCloseMobile={() => setIsMobileSidebarOpen(false)}
        reportsCount={activePatient?.documents?.length || documents.length}
      />

      {/* Main App Container */}
      <div className="main-wrapper">
        {/* Top Header Bar */}
        <TopBar
          patients={patients}
          activePatient={activePatient}
          onSelectPatient={(id) => openPatient(id, false)}
          onNewPatient={() => {
            setActivePatient(null)
            setActiveDocument(null)
            setStage('profile')
          }}
          onOpenHelp={() => setIsHelpOpen(true)}
          onToggleMobileSidebar={() => setIsMobileSidebarOpen(!isMobileSidebarOpen)}
        />

        {/* Scrollable Main Content Region */}
        <main id="main-content" tabIndex="-1" role="main" className="main-content">
          {/* WCAG 4.1.3 Screen Reader Live Announcement Region */}
          <div
            id="a11y-live-region"
            className="sr-only"
            aria-live="polite"
            aria-atomic="true"
          >
            {error ? `Alert: ${error}` : (loading ? 'Loading clinical data...' : `Current workflow stage: ${stage}`)}
          </div>
          {/* Contextual Breadcrumbs */}
          <Breadcrumbs
            stage={stage}
            activePatient={activePatient}
            activeDocument={activeDocument}
            onNavigate={(newStage) => setStage(newStage)}
          />

          {/* System Error Notification */}
          {error && (
            <div className="error" role="alert" aria-live="assertive" style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}>
              <span>{error}</span>
              <button
                className="secondary-btn btn-sm"
                onClick={() => setError('')}
              >
                Dismiss
              </button>
            </div>
          )}

          {/* Active Workflow Page */}
          {renderCurrentStage()}
        </main>
      </div>

      {/* Settings Modal */}
      <SettingsModal
        isOpen={isSettingsOpen}
        onClose={() => setIsSettingsOpen(false)}
        health={health}
        documentsCount={documents.length}
        patientsCount={patients.length}
      />

      {/* Clinical Help & Principles Modal */}
      <HelpModal
        isOpen={isHelpOpen}
        onClose={() => setIsHelpOpen(false)}
      />
    </div>
  )
}
