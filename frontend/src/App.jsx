import React, { useState } from 'react'
import Sidebar from './components/Sidebar'
import TopBar from './components/TopBar'
import Breadcrumbs from './components/Breadcrumbs'
import HelpModal from './components/HelpModal'
import SettingsModal from './components/SettingsModal'
import WorkflowStage from './WorkflowStage'
import { useWorkspace } from './useWorkspace'

export default function App() {
  const workspace = useWorkspace()
  const [isHelpOpen, setIsHelpOpen] = useState(false)
  const [isSettingsOpen, setIsSettingsOpen] = useState(false)
  const [isMobileSidebarOpen, setIsMobileSidebarOpen] = useState(false)

  const {
    stage, setStage, health, documents, patients, activePatient, activeDocument,
    loading, error, setError
  } = workspace

  return (
    <div className="app-shell">
      <a href="#main-content" className="skip-link">Skip to main content</a>
      <Sidebar
        currentStage={stage}
        onSelectStage={setStage}
        onOpenSettings={() => setIsSettingsOpen(true)}
        isOpenMobile={isMobileSidebarOpen}
        onCloseMobile={() => setIsMobileSidebarOpen(false)}
        reportsCount={activePatient?.documents?.length || documents.length}
      />

      <div className="main-wrapper">
        <TopBar
          patients={patients}
          activePatient={activePatient}
          onSelectPatient={(id) => workspace.openPatient(id, false)}
          onNewPatient={workspace.startNewPatient}
          onOpenHelp={() => setIsHelpOpen(true)}
          onToggleMobileSidebar={() => setIsMobileSidebarOpen((open) => !open)}
          isOpenMobile={isMobileSidebarOpen}
        />

        <main id="main-content" tabIndex="-1" role="main" className="main-content" aria-busy={loading}>
          <div id="a11y-live-region" className="sr-only" aria-live="polite" aria-atomic="true">
            {error ? `Alert: ${error}` : (loading ? 'Loading clinical data...' : `Current workflow stage: ${stage}`)}
          </div>
          <Breadcrumbs stage={stage} activePatient={activePatient} activeDocument={activeDocument} onNavigate={setStage} />
          {error && (
            <div className="error" role="alert" aria-live="assertive" aria-label="Clinical service error">
              <span>{error}</span>
              <button type="button" className="secondary-btn btn-sm" onClick={() => setError('')}>Dismiss</button>
            </div>
          )}
          <WorkflowStage workspace={workspace} />
        </main>
      </div>

      <SettingsModal isOpen={isSettingsOpen} onClose={() => setIsSettingsOpen(false)} health={health} documentsCount={documents.length} patientsCount={patients.length} />
      <HelpModal isOpen={isHelpOpen} onClose={() => setIsHelpOpen(false)} />
    </div>
  )
}
