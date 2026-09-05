import React, { useState, useEffect, useRef } from 'react'
import ProvenanceBadge from './ProvenanceBadge'
import { IconPatient, IconReports } from './Icons'

function parseInitialSymptoms(symptomsList) {
  if (!symptomsList || !Array.isArray(symptomsList) || symptomsList.length === 0) {
    return [{ name: '', onset: '', note: '' }]
  }
  return symptomsList.map(item => {
    if (typeof item === 'object' && item !== null) {
      return { name: item.name || '', onset: item.onset || '', note: item.note || '' }
    }
    const str = String(item).trim()
    return { name: str, onset: '', note: '' }
  })
}

function parseInitialConditions(conditionsList) {
  if (!conditionsList || !Array.isArray(conditionsList) || conditionsList.length === 0) {
    return [{ name: '' }]
  }
  return conditionsList.map(c => {
    if (typeof c === 'object' && c !== null) return { name: c.name || '' }
    return { name: String(c).trim() }
  })
}

function parseInitialAllergies(allergiesList) {
  if (!allergiesList || !Array.isArray(allergiesList) || allergiesList.length === 0) {
    return [{ allergen: '', reaction: '', severity: '' }]
  }
  return allergiesList.map(a => {
    if (typeof a === 'object' && a !== null) {
      return { allergen: a.allergen || a.name || '', reaction: a.reaction || '', severity: a.severity || '' }
    }
    const str = String(a).trim()
    return { allergen: str, reaction: '', severity: '' }
  })
}

function parseInitialMedications(medicationsList) {
  if (!medicationsList || !Array.isArray(medicationsList) || medicationsList.length === 0) {
    return [{ name: '', dose: '', frequency: '', notes: '' }]
  }
  return medicationsList.map(m => {
    if (typeof m === 'object' && m !== null) {
      return { name: m.name || '', dose: m.dose || '', frequency: m.frequency || '', notes: m.notes || '' }
    }
    const str = String(m).trim()
    return { name: str, dose: '', frequency: '', notes: '' }
  })
}

export default function PatientProfilePage({
  activePatient,
  onSavePatient,
  onProceedToReports,
  loading
}) {
  const [name, setName] = useState('')
  const [age, setAge] = useState('')
  const [sex, setSex] = useState('')
  const [notes, setNotes] = useState('')

  const [symptoms, setSymptoms] = useState([{ name: '', onset: '', note: '' }])
  const [conditions, setConditions] = useState([{ name: '' }])
  const [allergies, setAllergies] = useState([{ allergen: '', reaction: '', severity: '' }])
  const [medications, setMedications] = useState([{ name: '', dose: '', frequency: '', notes: '' }])

  const [errors, setErrors] = useState({})
  const [isDirty, setIsDirty] = useState(false)
  const [savedSuccess, setSavedSuccess] = useState(false)
  const isInitialMount = useRef(true)

  useEffect(() => {
    if (activePatient) {
      setName(activePatient.name || '')
      setAge(activePatient.age != null ? String(activePatient.age) : '')
      setSex(activePatient.sex || '')
      setNotes(activePatient.notes || '')
      setSymptoms(parseInitialSymptoms(activePatient.symptoms))
      setConditions(parseInitialConditions(activePatient.conditions))
      setAllergies(parseInitialAllergies(activePatient.allergies))
      setMedications(parseInitialMedications(activePatient.medications))
    } else {
      setName('')
      setAge('')
      setSex('')
      setNotes('')
      setSymptoms([{ name: '', onset: '', note: '' }])
      setConditions([{ name: '' }])
      setAllergies([{ allergen: '', reaction: '', severity: '' }])
      setMedications([{ name: '', dose: '', frequency: '', notes: '' }])
    }
    setErrors({})
    setIsDirty(false)
    setSavedSuccess(false)
    isInitialMount.current = true
  }, [activePatient])

  function markDirty() {
    if (isInitialMount.current) {
      isInitialMount.current = false
      return
    }
    setIsDirty(true)
    setSavedSuccess(false)
  }

  const addSymptom = () => {
    setSymptoms([...symptoms, { name: '', onset: '', note: '' }])
    markDirty()
  }
  const updateSymptom = (index, field, value) => {
    const next = [...symptoms]
    next[index][field] = value
    setSymptoms(next)
    markDirty()
  }
  const removeSymptom = (index) => {
    if (symptoms.length <= 1) setSymptoms([{ name: '', onset: '', note: '' }])
    else setSymptoms(symptoms.filter((_, i) => i !== index))
    markDirty()
  }

  const addCondition = () => {
    setConditions([...conditions, { name: '' }])
    markDirty()
  }
  const updateCondition = (index, value) => {
    const next = [...conditions]
    next[index].name = value
    setConditions(next)
    markDirty()
  }
  const removeCondition = (index) => {
    if (conditions.length <= 1) setConditions([{ name: '' }])
    else setConditions(conditions.filter((_, i) => i !== index))
    markDirty()
  }

  const addAllergy = () => {
    setAllergies([...allergies, { allergen: '', reaction: '', severity: '' }])
    markDirty()
  }
  const updateAllergy = (index, field, value) => {
    const next = [...allergies]
    next[index][field] = value
    setAllergies(next)
    markDirty()
  }
  const removeAllergy = (index) => {
    if (allergies.length <= 1) setAllergies([{ allergen: '', reaction: '', severity: '' }])
    else setAllergies(allergies.filter((_, i) => i !== index))
    markDirty()
  }

  const addMedication = () => {
    setMedications([...medications, { name: '', dose: '', frequency: '', notes: '' }])
    markDirty()
  }
  const updateMedication = (index, field, value) => {
    const next = [...medications]
    next[index][field] = value
    setMedications(next)
    markDirty()
  }
  const removeMedication = (index) => {
    if (medications.length <= 1) setMedications([{ name: '', dose: '', frequency: '', notes: '' }])
    else setMedications(medications.filter((_, i) => i !== index))
    markDirty()
  }

  function validate() {
    const newErrors = {}
    if (!name.trim()) newErrors.name = 'Patient name or anonymous identifier is required.'
    if (age.trim()) {
      const parsedAge = parseInt(age, 10)
      if (isNaN(parsedAge) || parsedAge < 0 || parsedAge > 130) {
        newErrors.age = 'Enter a valid age between 0 and 130.'
      }
    }
    setErrors(newErrors)
    return Object.keys(newErrors).length === 0
  }

  async function handleSubmit(e) {
    if (e) e.preventDefault()
    if (!validate()) return

    const cleanedSymptoms = symptoms
      .filter(s => s.name && s.name.trim())
      .map(s => {
        const parts = [s.name.trim()]
        if (s.onset && s.onset.trim()) parts.push(`onset: ${s.onset.trim()}`)
        if (s.note && s.note.trim()) parts.push(`note: ${s.note.trim()}`)
        return parts.length > 1 ? `${parts[0]} (${parts.slice(1).join(', ')})` : parts[0]
      })

    const cleanedConditions = conditions.map(c => c.name.trim()).filter(Boolean)

    const cleanedAllergies = allergies
      .filter(a => a.allergen && a.allergen.trim())
      .map(a => {
        const details = []
        if (a.reaction && a.reaction.trim()) details.push(`reaction: ${a.reaction.trim()}`)
        if (a.severity && a.severity.trim()) details.push(`severity: ${a.severity.trim()}`)
        return details.length > 0 ? `${a.allergen.trim()} (${details.join(', ')})` : a.allergen.trim()
      })

    const cleanedMedications = medications
      .filter(m => m.name && m.name.trim())
      .map(m => {
        const parts = []
        if (m.dose && m.dose.trim()) parts.push(m.dose.trim())
        if (m.frequency && m.frequency.trim()) parts.push(m.frequency.trim())
        if (m.notes && m.notes.trim()) parts.push(`notes: ${m.notes.trim()}`)
        return parts.length > 0 ? `${m.name.trim()} - ${parts.join(', ')}` : m.name.trim()
      })

    const payload = {
      name: name.trim(),
      age: age.trim() ? parseInt(age, 10) : null,
      sex: sex.trim() || null,
      symptoms: cleanedSymptoms,
      conditions: cleanedConditions,
      allergies: cleanedAllergies,
      medications: cleanedMedications,
      notes: notes.trim()
    }

    try {
      await onSavePatient(payload)
      setIsDirty(false)
      setSavedSuccess(true)
      setTimeout(() => setSavedSuccess(false), 3500)
    } catch {
      // Handled by App
    }
  }

  return (
    <div className="page-grid two-col">
      <div className="card">
        <div className="section-head">
          <div>
            <div style={{ display: 'flex', alignItems: 'center', gap: '0.5rem' }}>
              <h2>{activePatient ? 'Edit Patient Profile' : 'New Patient Intake'}</h2>
              <ProvenanceBadge type="user_provided" size="small" />
            </div>
            <div className="small muted">
              All data entered in this form is classified as <strong>User-Provided</strong> context.
            </div>
          </div>
        </div>

        {/* Unsaved Changes Banner */}
        {isDirty && (
          <div
            style={{
              padding: '0.6rem 0.85rem',
              backgroundColor: 'var(--status-warning-bg)',
              border: '1px solid var(--status-warning-border)',
              borderRadius: 'var(--radius-input)',
              fontSize: '13px',
              color: 'var(--status-warning)',
              display: 'flex',
              alignItems: 'center',
              justifyContent: 'space-between',
              marginBottom: '1rem'
            }}
          >
            <span>● Unsaved modifications in intake form</span>
            <button
              type="button"
              className="primary-btn btn-sm"
              onClick={handleSubmit}
              disabled={loading}
            >
              {loading ? 'Saving...' : 'Save Now'}
            </button>
          </div>
        )}

        <form onSubmit={handleSubmit} noValidate style={{ display: 'grid', gap: '1.5rem' }}>
          {/* Section 1: Basic Information */}
          <fieldset style={{ border: 'none', padding: 0, margin: 0 }}>
            <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: '0.75rem', borderBottom: '1px solid var(--border-subtle)', paddingBottom: '0.35rem' }}>
              <legend style={{ fontSize: '14px', fontWeight: 600, color: 'var(--text-primary)', margin: 0 }}>
                1. Basic Information
              </legend>
              <ProvenanceBadge type="user_provided" size="small" source="patient intake" />
            </div>

            <div style={{ display: 'grid', gap: '0.85rem' }}>
              <div>
                <label htmlFor="patient-name">
                  Patient Identifier or Full Name <span style={{ color: 'var(--status-danger)' }}>*</span>
                </label>
                <input
                  id="patient-name"
                  type="text"
                  value={name}
                  onChange={e => {
                    setName(e.target.value)
                    markDirty()
                    if (errors.name) {
                      const next = { ...errors }
                      delete next.name
                      setErrors(next)
                    }
                  }}
                  placeholder="e.g., Sarah Jenkins or PT-80492"
                  style={{ borderColor: errors.name ? 'var(--status-danger)' : undefined }}
                  aria-invalid={errors.name ? 'true' : 'false'}
                  aria-describedby={errors.name ? 'name-error' : undefined}
                />
                {errors.name && (
                  <div id="name-error" className="small" style={{ color: 'var(--status-danger)', marginTop: '0.25rem' }}>
                    {errors.name}
                  </div>
                )}
              </div>

              <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: '0.85rem' }}>
                <div>
                  <label htmlFor="patient-age">
                    Age <span className="muted" style={{ fontWeight: 400 }}>(optional)</span>
                  </label>
                  <input
                    id="patient-age"
                    type="number"
                    min="0"
                    max="130"
                    value={age}
                    onChange={e => {
                      setAge(e.target.value)
                      markDirty()
                      if (errors.age) {
                        const next = { ...errors }
                        delete next.age
                        setErrors(next)
                      }
                    }}
                    placeholder="e.g., 42"
                    style={{ borderColor: errors.age ? 'var(--status-danger)' : undefined }}
                    aria-invalid={errors.age ? 'true' : 'false'}
                    aria-describedby={errors.age ? 'age-error' : undefined}
                  />
                  {errors.age && (
                    <div id="age-error" className="small" style={{ color: 'var(--status-danger)', marginTop: '0.25rem' }}>
                      {errors.age}
                    </div>
                  )}
                </div>

                <div>
                  <label htmlFor="patient-sex">
                    Biological Sex <span className="muted" style={{ fontWeight: 400 }}>(optional)</span>
                  </label>
                  <select
                    id="patient-sex"
                    value={sex}
                    onChange={e => {
                      setSex(e.target.value)
                      markDirty()
                    }}
                  >
                    <option value="">Not specified</option>
                    <option value="Female">Female</option>
                    <option value="Male">Male</option>
                    <option value="Other">Other / Intersex</option>
                  </select>
                </div>
              </div>
            </div>
          </fieldset>

          {/* Section 2: Current Symptoms (Repeatable) */}
          <fieldset style={{ border: 'none', padding: 0, margin: 0 }}>
            <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: '0.75rem', borderBottom: '1px solid var(--border-subtle)', paddingBottom: '0.35rem' }}>
              <legend style={{ fontSize: '14px', fontWeight: 600, color: 'var(--text-primary)', margin: 0 }}>
                2. Current Symptoms <span className="muted" style={{ fontWeight: 400 }}>(repeatable)</span>
              </legend>
              <button
                type="button"
                className="secondary-btn btn-sm"
                onClick={addSymptom}
                style={{ padding: '0.2rem 0.5rem' }}
              >
                + Add Symptom
              </button>
            </div>

            <div className="stack gap-sm">
              {symptoms.map((sym, idx) => (
                <div
                  key={idx}
                  style={{
                    padding: '0.75rem',
                    background: 'var(--bg-subtle)',
                    borderRadius: 'var(--radius-input)',
                    border: '1px solid var(--border-color)',
                    display: 'grid',
                    gap: '0.5rem'
                  }}
                >
                  <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}>
                    <span className="small muted" style={{ fontWeight: 600 }}>Symptom Entry #{idx + 1}</span>
                    <button
                      type="button"
                      className="secondary-btn btn-sm"
                      onClick={() => removeSymptom(idx)}
                      style={{ padding: '0.15rem 0.45rem', fontSize: '11px', color: 'var(--text-muted)' }}
                      title="Remove symptom entry"
                    >
                      Remove
                    </button>
                  </div>

                  <div style={{ display: 'grid', gridTemplateColumns: '1.5fr 1fr', gap: '0.5rem' }}>
                    <div>
                      <label htmlFor={`symptom-name-${idx}`}>Symptom Name</label>
                      <input
                        id={`symptom-name-${idx}`}
                        type="text"
                        value={sym.name}
                        onChange={e => updateSymptom(idx, 'name', e.target.value)}
                        placeholder="e.g., Shortness of breath"
                      />
                    </div>
                    <div>
                      <label htmlFor={`symptom-onset-${idx}`}>
                        Onset / Duration <span className="muted" style={{ fontWeight: 400 }}>(optional)</span>
                      </label>
                      <input
                        id={`symptom-onset-${idx}`}
                        type="text"
                        value={sym.onset}
                        onChange={e => updateSymptom(idx, 'onset', e.target.value)}
                        placeholder="e.g., 3 days, intermittent"
                      />
                    </div>
                  </div>

                  <div>
                    <label htmlFor={`symptom-note-${idx}`}>
                      Symptom Notes <span className="muted" style={{ fontWeight: 400 }}>(optional)</span>
                    </label>
                    <input
                      id={`symptom-note-${idx}`}
                      type="text"
                      value={sym.note}
                      onChange={e => updateSymptom(idx, 'note', e.target.value)}
                      placeholder="e.g., Worsens during exertion or lying flat"
                    />
                  </div>
                </div>
              ))}
            </div>
          </fieldset>

          {/* Section 3: Existing Conditions (Repeatable) */}
          <fieldset style={{ border: 'none', padding: 0, margin: 0 }}>
            <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: '0.75rem', borderBottom: '1px solid var(--border-subtle)', paddingBottom: '0.35rem' }}>
              <legend style={{ fontSize: '14px', fontWeight: 600, color: 'var(--text-primary)', margin: 0 }}>
                3. Existing Conditions <span className="muted" style={{ fontWeight: 400 }}>(repeatable)</span>
              </legend>
              <button
                type="button"
                className="secondary-btn btn-sm"
                onClick={addCondition}
                style={{ padding: '0.2rem 0.5rem' }}
              >
                + Add Condition
              </button>
            </div>

            <div className="stack gap-sm">
              {conditions.map((cond, idx) => (
                <div
                  key={idx}
                  style={{
                    display: 'flex',
                    alignItems: 'center',
                    gap: '0.5rem'
                  }}
                >
                  <div style={{ flex: 1 }}>
                    <input
                      id={`condition-${idx}`}
                      type="text"
                      value={cond.name}
                      onChange={e => updateCondition(idx, e.target.value)}
                      placeholder={`e.g., Hypertension, Type 2 Diabetes (#${idx + 1})`}
                    />
                  </div>
                  <button
                    type="button"
                    className="secondary-btn btn-sm"
                    onClick={() => removeCondition(idx)}
                    style={{ padding: '0.4rem 0.6rem', color: 'var(--text-muted)' }}
                    title="Remove condition"
                  >
                    ✕
                  </button>
                </div>
              ))}
            </div>
          </fieldset>

          {/* Section 4: Allergies (Repeatable) */}
          <fieldset style={{ border: 'none', padding: 0, margin: 0 }}>
            <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: '0.75rem', borderBottom: '1px solid var(--border-subtle)', paddingBottom: '0.35rem' }}>
              <legend style={{ fontSize: '14px', fontWeight: 600, color: 'var(--text-primary)', margin: 0 }}>
                4. Allergies <span className="muted" style={{ fontWeight: 400 }}>(repeatable)</span>
              </legend>
              <button
                type="button"
                className="secondary-btn btn-sm"
                onClick={addAllergy}
                style={{ padding: '0.2rem 0.5rem' }}
              >
                + Add Allergy
              </button>
            </div>

            <div className="stack gap-sm">
              {allergies.map((allg, idx) => (
                <div
                  key={idx}
                  style={{
                    padding: '0.75rem',
                    background: 'var(--bg-subtle)',
                    borderRadius: 'var(--radius-input)',
                    border: '1px solid var(--border-color)',
                    display: 'grid',
                    gap: '0.5rem'
                  }}
                >
                  <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}>
                    <span className="small muted" style={{ fontWeight: 600 }}>Allergen Entry #{idx + 1}</span>
                    <button
                      type="button"
                      className="secondary-btn btn-sm"
                      onClick={() => removeAllergy(idx)}
                      style={{ padding: '0.15rem 0.45rem', fontSize: '11px', color: 'var(--text-muted)' }}
                    >
                      Remove
                    </button>
                  </div>

                  <div style={{ display: 'grid', gridTemplateColumns: '1.2fr 1fr 1fr', gap: '0.5rem' }}>
                    <div>
                      <label htmlFor={`allergen-${idx}`}>Allergen Name</label>
                      <input
                        id={`allergen-${idx}`}
                        type="text"
                        value={allg.allergen}
                        onChange={e => updateAllergy(idx, 'allergen', e.target.value)}
                        placeholder="e.g., Penicillin, Latex"
                      />
                    </div>
                    <div>
                      <label htmlFor={`allergy-reaction-${idx}`}>
                        Reaction <span className="muted" style={{ fontWeight: 400 }}>(optional)</span>
                      </label>
                      <input
                        id={`allergy-reaction-${idx}`}
                        type="text"
                        value={allg.reaction}
                        onChange={e => updateAllergy(idx, 'reaction', e.target.value)}
                        placeholder="e.g., Hives, Anaphylaxis"
                      />
                    </div>
                    <div>
                      <label htmlFor={`allergy-severity-${idx}`}>
                        Severity <span className="muted" style={{ fontWeight: 400 }}>(optional)</span>
                      </label>
                      <select
                        id={`allergy-severity-${idx}`}
                        value={allg.severity}
                        onChange={e => updateAllergy(idx, 'severity', e.target.value)}
                      >
                        <option value="">Unspecified</option>
                        <option value="Mild">Mild</option>
                        <option value="Moderate">Moderate</option>
                        <option value="Severe">Severe</option>
                      </select>
                    </div>
                  </div>
                </div>
              ))}
            </div>
          </fieldset>

          {/* Section 5: Medications (Repeatable) */}
          <fieldset style={{ border: 'none', padding: 0, margin: 0 }}>
            <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: '0.75rem', borderBottom: '1px solid var(--border-subtle)', paddingBottom: '0.35rem' }}>
              <legend style={{ fontSize: '14px', fontWeight: 600, color: 'var(--text-primary)', margin: 0 }}>
                5. Current Medications <span className="muted" style={{ fontWeight: 400 }}>(repeatable)</span>
              </legend>
              <button
                type="button"
                className="secondary-btn btn-sm"
                onClick={addMedication}
                style={{ padding: '0.2rem 0.5rem' }}
              >
                + Add Medication
              </button>
            </div>

            <div className="stack gap-sm">
              {medications.map((med, idx) => (
                <div
                  key={idx}
                  style={{
                    padding: '0.75rem',
                    background: 'var(--bg-subtle)',
                    borderRadius: 'var(--radius-input)',
                    border: '1px solid var(--border-color)',
                    display: 'grid',
                    gap: '0.5rem'
                  }}
                >
                  <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}>
                    <span className="small muted" style={{ fontWeight: 600 }}>Medication #{idx + 1}</span>
                    <button
                      type="button"
                      className="secondary-btn btn-sm"
                      onClick={() => removeMedication(idx)}
                      style={{ padding: '0.15rem 0.45rem', fontSize: '11px', color: 'var(--text-muted)' }}
                    >
                      Remove
                    </button>
                  </div>

                  <div style={{ display: 'grid', gridTemplateColumns: '1.2fr 1fr 1fr', gap: '0.5rem' }}>
                    <div>
                      <label htmlFor={`med-name-${idx}`}>Medication Name</label>
                      <input
                        id={`med-name-${idx}`}
                        type="text"
                        value={med.name}
                        onChange={e => updateMedication(idx, 'name', e.target.value)}
                        placeholder="e.g., Lisinopril, Metformin"
                      />
                    </div>
                    <div>
                      <label htmlFor={`med-dose-${idx}`}>
                        Dose <span className="muted" style={{ fontWeight: 400 }}>(optional)</span>
                      </label>
                      <input
                        id={`med-dose-${idx}`}
                        type="text"
                        value={med.dose}
                        onChange={e => updateMedication(idx, 'dose', e.target.value)}
                        placeholder="e.g., 10 mg"
                      />
                    </div>
                    <div>
                      <label htmlFor={`med-freq-${idx}`}>
                        Frequency <span className="muted" style={{ fontWeight: 400 }}>(optional)</span>
                      </label>
                      <input
                        id={`med-freq-${idx}`}
                        type="text"
                        value={med.frequency}
                        onChange={e => updateMedication(idx, 'frequency', e.target.value)}
                        placeholder="e.g., Once daily"
                      />
                    </div>
                  </div>

                  <div>
                    <label htmlFor={`med-notes-${idx}`}>
                      Medication Notes <span className="muted" style={{ fontWeight: 400 }}>(optional)</span>
                    </label>
                    <input
                      id={`med-notes-${idx}`}
                      type="text"
                      value={med.notes}
                      onChange={e => updateMedication(idx, 'notes', e.target.value)}
                      placeholder="e.g., Taken with food in the morning"
                    />
                  </div>
                </div>
              ))}
            </div>
          </fieldset>

          {/* Section 6: Additional Context (Multiline) */}
          <fieldset style={{ border: 'none', padding: 0, margin: 0 }}>
            <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: '0.75rem', borderBottom: '1px solid var(--border-subtle)', paddingBottom: '0.35rem' }}>
              <legend style={{ fontSize: '14px', fontWeight: 600, color: 'var(--text-primary)', margin: 0 }}>
                6. Additional Clinical Context
              </legend>
              <ProvenanceBadge type="user_provided" size="small" source="patient intake" />
            </div>
            <label htmlFor="patient-notes">
              Free-Text Observations & Background <span className="muted" style={{ fontWeight: 400 }}>(optional)</span>
            </label>
            <textarea
              id="patient-notes"
              rows={3}
              value={notes}
              onChange={e => {
                setNotes(e.target.value)
                markDirty()
              }}
              placeholder="Additional background context, family history notes, or clinical inquiry objectives..."
            />
          </fieldset>

          {/* Submission & Action Bar */}
          <div style={{ display: 'flex', gap: '0.75rem', alignItems: 'center', paddingTop: '0.5rem', borderTop: '1px solid var(--border-subtle)' }}>
            <button
              type="submit"
              disabled={loading || !name.trim()}
              className="primary-btn"
            >
              {loading ? 'Saving...' : activePatient ? 'Save Patient Context' : 'Create Patient Context'}
            </button>
            {savedSuccess && (
              <span className="small" style={{ color: 'var(--status-success)', fontWeight: 600 }}>
                ✓ Patient context saved successfully
              </span>
            )}
          </div>
        </form>
      </div>

      <div className="card tall">
        <div className="section-head">
          <div>
            <h3>Active Patient Context Summary</h3>
            <div className="small muted">Review how user-provided data is established before attaching reports.</div>
          </div>
          {activePatient && (
            <button onClick={onProceedToReports} className="primary-btn">
              Next: Upload Reports →
            </button>
          )}
        </div>

        {!activePatient ? (
          <div className="muted small" style={{ marginTop: '2rem', textAlign: 'center' }}>
            No patient selected. Complete the form to establish patient context.
          </div>
        ) : (
          <div className="stack gap-md" style={{ marginTop: '1rem' }}>
            <div style={{ padding: '1rem', background: 'var(--bg-subtle)', borderRadius: 'var(--radius-input)', border: '1px solid var(--border-color)' }}>
              <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}>
                <strong style={{ fontSize: '1.2rem', color: 'var(--text-primary)' }}>{activePatient.name}</strong>
                <ProvenanceBadge type="user_provided" size="small" />
              </div>
              <div className="small muted" style={{ marginTop: '0.25rem' }}>
                {activePatient.age ? `${activePatient.age} years old` : 'Age unrecorded'} · {activePatient.sex || 'Sex unrecorded'}
              </div>
            </div>

            <div>
              <div className="section-title mini">Reported Symptoms</div>
              <div className="tag-wrap">
                {activePatient.symptoms?.length ? (
                  activePatient.symptoms.map(s => <span className="tag secondary" key={s}>{s}</span>)
                ) : (
                  <span className="small muted">None reported</span>
                )}
              </div>
            </div>

            <div>
              <div className="section-title mini">Known Conditions & Allergies</div>
              <div className="tag-wrap">
                {activePatient.conditions?.map(c => <span className="tag" key={c}>{c}</span>)}
                {activePatient.allergies?.map(a => <span className="tag secondary" key={a}>Allergy: {a}</span>)}
                {!activePatient.conditions?.length && !activePatient.allergies?.length && (
                  <span className="small muted">No conditions or allergies documented</span>
                )}
              </div>
            </div>

            <div>
              <div className="section-title mini">Current Medications</div>
              <div className="tag-wrap">
                {activePatient.medications?.length ? (
                  activePatient.medications.map(m => <span className="tag" key={m}>{m}</span>)
                ) : (
                  <span className="small muted">No active medications recorded</span>
                )}
              </div>
            </div>

            {activePatient.notes && (
              <div>
                <div className="section-title mini">Clinical Notes</div>
                <div style={{ padding: '0.75rem', background: 'var(--bg-subtle)', borderRadius: 'var(--radius-input)', border: '1px solid var(--border-color)', fontSize: '0.9rem' }}>
                  {activePatient.notes}
                </div>
              </div>
            )}

            <div>
              <div className="section-title mini">Attached Medical Reports ({activePatient.documents?.length || 0})</div>
              {(!activePatient.documents || activePatient.documents.length === 0) ? (
                <div className="small muted">
                  No reports uploaded yet. Click <strong>Next: Upload Reports →</strong> to attach laboratory or clinical documents.
                </div>
              ) : (
                <div className="doc-list" style={{ marginTop: '0.5rem' }}>
                  {activePatient.documents.map(doc => (
                    <div key={doc.document_id} style={{ display: 'flex', justifyContent: 'space-between', padding: '0.6rem 0.8rem', background: 'var(--bg-surface)', borderRadius: 'var(--radius-input)', border: '1px solid var(--border-color)', alignItems: 'center' }}>
                      <div>
                        <strong>{doc.title}</strong>
                        <div className="small muted">Processed: {doc.created_at?.slice(0, 10)}</div>
                      </div>
                      <ProvenanceBadge type="source_extracted" size="small" />
                    </div>
                  ))}
                </div>
              )}
            </div>
          </div>
        )}
      </div>
    </div>
  )
}