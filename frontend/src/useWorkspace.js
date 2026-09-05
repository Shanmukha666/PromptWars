import { useCallback, useEffect, useState } from 'react'
import { DEMO_DATA } from './demoData'
import { request } from './apiClient'

export function useWorkspace() {
  const [stage, setStage] = useState('overview')
  const [health, setHealth] = useState(null)
  const [documents, setDocuments] = useState([])
  const [patients, setPatients] = useState([])
  const [activePatient, setActivePatient] = useState(null)
  const [activeDocument, setActiveDocument] = useState(null)
  const [loading, setLoading] = useState(false)
  const [error, setError] = useState('')
  const [isDemoMode, setIsDemoMode] = useState(false)

  const openDocument = useCallback(async (documentId) => {
    setLoading(true)
    setError('')
    try {
      if (isDemoMode) {
        const document = documents.find((candidate) => candidate.document_id === documentId) ||
          activePatient?.documents?.find((candidate) => candidate.document_id === documentId) ||
          DEMO_DATA.patients[0].documents[0]
        setActiveDocument(document)
        return
      }
      setActiveDocument(await request(`/api/documents/${documentId}`))
    } catch (requestError) {
      setError(requestError.message)
    } finally {
      setLoading(false)
    }
  }, [activePatient, documents, isDemoMode])

  const openPatient = useCallback(async (patientId, navigateToProfile = true) => {
    setLoading(true)
    setError('')
    try {
      if (isDemoMode) {
        const patient = patients.find((candidate) => candidate.patient_id === patientId) || DEMO_DATA.patients[0]
        setActivePatient(patient)
        setActiveDocument(patient?.documents?.[0] || null)
        if (navigateToProfile) setStage('profile')
        return
      }
      const patient = await request(`/api/patients/${patientId}`)
      setActivePatient(patient)
      if (patient.documents?.length > 0) {
        setActiveDocument(await request(`/api/documents/${patient.documents[0].document_id}`))
      } else {
        setActiveDocument(null)
      }
      if (navigateToProfile) setStage('profile')
    } catch (requestError) {
      setError(requestError.message)
    } finally {
      setLoading(false)
    }
  }, [isDemoMode, patients])

  const refreshAll = useCallback(async () => {
    try {
      const [healthData, documentsData, patientsData] = await Promise.all([
        request('/api/health'),
        request('/api/documents'),
        request('/api/patients')
      ])
      setHealth(healthData)
      setDocuments(documentsData.items || [])
      setPatients(patientsData.items || [])
      setIsDemoMode(false)
      const patientId = activePatient?.patient_id || patientsData.items?.[0]?.patient_id
      if (patientId) await openPatient(patientId, false)
    } catch (requestError) {
      console.warn('Backend API unavailable; initializing synthetic browser demo mode')
      setIsDemoMode(true)
      setHealth(DEMO_DATA.health)
      setPatients(DEMO_DATA.patients)
      setDocuments(DEMO_DATA.patients.flatMap((patient) => patient.documents || []))
      if (!activePatient && DEMO_DATA.patients.length > 0) {
        const patient = DEMO_DATA.patients[0]
        setActivePatient(patient)
        setActiveDocument(patient.documents?.[0] || null)
      }
    }
  }, [activePatient, openPatient])

  useEffect(() => {
    refreshAll().catch(() => {})
  }, [])

  const savePatient = useCallback(async (payload) => {
    setLoading(true)
    setError('')
    try {
      if (activePatient?.patient_id) {
        await request(`/api/patients/${activePatient.patient_id}`, {
          method: 'PUT', headers: { 'Content-Type': 'application/json' }, body: JSON.stringify(payload)
        })
        await openPatient(activePatient.patient_id, false)
      } else {
        const response = await request('/api/patients', {
          method: 'POST', headers: { 'Content-Type': 'application/json' }, body: JSON.stringify(payload)
        })
        await refreshAll()
        await openPatient(response.patient_id, true)
      }
    } catch (requestError) {
      setError(requestError.message)
    } finally {
      setLoading(false)
    }
  }, [activePatient, openPatient, refreshAll])

  const uploadFile = useCallback(async (file, title) => {
    if (!file) return
    setLoading(true)
    setError('')
    try {
      const body = new FormData()
      body.append('file', file)
      if (title.trim()) body.append('title', title.trim())
      if (activePatient?.patient_id) body.append('patient_id', activePatient.patient_id)
      const response = await request('/api/ingest/file', { method: 'POST', body })
      await refreshAll()
      await openDocument(response.document_id)
      setStage('structured')
    } catch (requestError) {
      setError(requestError.message)
    } finally {
      setLoading(false)
    }
  }, [activePatient, openDocument, refreshAll])

  const uploadText = useCallback(async (text, title) => {
    if (!text.trim()) return
    setLoading(true)
    setError('')
    try {
      const response = await request('/api/ingest/text', {
        method: 'POST', headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ title: title.trim() || 'Clinical Report Text', text, patient_id: activePatient?.patient_id || null })
      })
      await refreshAll()
      await openDocument(response.document_id)
      setStage('structured')
    } catch (requestError) {
      setError(requestError.message)
    } finally {
      setLoading(false)
    }
  }, [activePatient, openDocument, refreshAll])

  const verifyOrEditLab = useCallback(async (verificationPayload) => {
    setLoading(true)
    setError('')
    try {
      if (isDemoMode) {
        if (activeDocument?.extracted?.labs) {
          const updatedLabs = { ...activeDocument.extracted.labs }
          const action = verificationPayload.action || 'verify'
          const key = verificationPayload.test_key || verificationPayload.test_name
          if (action === 'remove') delete updatedLabs[key]
          else if (action === 'add') {
            updatedLabs[key] = {
              test_name: verificationPayload.test_name || key,
              display_name: (verificationPayload.test_name || key).toUpperCase(),
              value: verificationPayload.value, unit: verificationPayload.unit || '',
              reference_range_raw: verificationPayload.reference_range_raw,
              reference_range_low: verificationPayload.reference_range_low,
              reference_range_high: verificationPayload.reference_range_high,
              reference_range_operator: verificationPayload.reference_range_operator || 'between',
              reference_range: verificationPayload.reference_range_low != null ? { min: verificationPayload.reference_range_low, max: verificationPayload.reference_range_high } : null,
              status: verificationPayload.status || 'not_assessed',
              source_snippet: verificationPayload.source_snippet || 'Clinician manual observation',
              verification_status: 'verified', provenance_type: 'user_verified'
            }
          } else if (updatedLabs[key]) {
            updatedLabs[key] = { ...updatedLabs[key], value: verificationPayload.value ?? updatedLabs[key].value, unit: verificationPayload.unit ?? updatedLabs[key].unit, status: verificationPayload.status ?? updatedLabs[key].status, verification_status: action === 'mark_incorrect' ? 'incorrect' : action === 'edit' ? 'edited' : 'verified', provenance_type: 'user_verified' }
          }
          setActiveDocument({ ...activeDocument, extracted: { ...activeDocument.extracted, labs: updatedLabs } })
        }
        return
      }
      const response = await request('/api/documents/verify-lab', {
        method: 'POST', headers: { 'Content-Type': 'application/json' }, body: JSON.stringify(verificationPayload)
      })
      if (response.document) setActiveDocument(response.document)
      if (activePatient?.patient_id) await openPatient(activePatient.patient_id, false)
    } catch (requestError) {
      setError(requestError.message)
    } finally {
      setLoading(false)
    }
  }, [activeDocument, activePatient, isDemoMode, openPatient])

  const startNewPatient = useCallback(() => {
    setActivePatient(null)
    setActiveDocument(null)
    setStage('profile')
  }, [])

  return { stage, setStage, health, documents, patients, activePatient, activeDocument, loading, error, setError, isDemoMode, openPatient, openDocument, savePatient, uploadFile, uploadText, verifyOrEditLab, startNewPatient }
}
