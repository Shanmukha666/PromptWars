import React from 'react'
import OverviewPage from './components/OverviewPage'
import PatientProfilePage from './components/PatientProfilePage'
import ReportsPage from './components/ReportsPage'
import StructuredRecordPage from './components/StructuredRecordPage'
import ReviewVerificationPage from './components/ReviewVerificationPage'
import TimelineHistoryPage from './components/TimelineHistoryPage'
import ProcessingEvidencePage from './components/ProcessingEvidencePage'

export default function WorkflowStage({ workspace }) {
  const {
    stage, setStage, patients, documents, activePatient, activeDocument,
    health, loading, openPatient, openDocument, startNewPatient,
    savePatient, uploadFile, uploadText, verifyOrEditLab
  } = workspace

  switch (stage) {
    case 'overview':
      return <OverviewPage patients={patients} activePatient={activePatient} onSelectPatient={(id) => openPatient(id, false)} onNewPatient={startNewPatient} documents={documents} health={health} onProceedToProfile={() => setStage('profile')} onSelectDocument={async (id) => { await openDocument(id); setStage('structured') }} onNavigateStage={setStage} />
    case 'profile':
      return <PatientProfilePage activePatient={activePatient} onSavePatient={savePatient} onProceedToReports={() => setStage('reports')} loading={loading} />
    case 'reports':
      return <ReportsPage activePatient={activePatient} activeDocument={activeDocument} onUploadFile={uploadFile} onUploadText={uploadText} onSelectDocument={openDocument} onProceedToStructured={() => setStage('structured')} loading={loading} />
    case 'structured':
      return <StructuredRecordPage activePatient={activePatient} activeDocument={activeDocument} onSelectDocument={openDocument} onProceedToReview={() => setStage('review')} onProceedToTimeline={() => setStage('timeline')} onNavigateStage={setStage} />
    case 'review':
      return <ReviewVerificationPage activePatient={activePatient} activeDocument={activeDocument} onSelectDocument={openDocument} onVerifyOrEditLab={verifyOrEditLab} onProceedToTimeline={() => setStage('timeline')} onNavigateStage={setStage} loading={loading} />
    case 'timeline':
      return <TimelineHistoryPage activePatient={activePatient} onSelectDocument={async (id) => { await openDocument(id); setStage('structured') }} />
    case 'processing':
      return <ProcessingEvidencePage activePatient={activePatient} activeDocument={activeDocument} onSelectDocument={openDocument} onNavigateStage={setStage} loading={loading} />
    default:
      return null
  }
}
