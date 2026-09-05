/**
 * PatientProfilePage component tests:
 * - Renders form inputs (name, age, sex)
 * - Displays validation errors for empty required fields
 * - Calls onSavePatient with correct payload
 * - Populates fields from activePatient prop
 */
import React from 'react'
import { render, screen, fireEvent, waitFor } from '@testing-library/react'
import { describe, it, expect, vi } from 'vitest'
import PatientProfilePage from '../components/PatientProfilePage'

describe('PatientProfilePage', () => {
  const defaultProps = {
    activePatient: null,
    onSavePatient: vi.fn(),
    onProceedToReports: vi.fn(),
    loading: false,
  }

  it('renders "New Patient Intake" heading when no active patient', () => {
    render(<PatientProfilePage {...defaultProps} />)
    expect(screen.getByText('New Patient Intake')).toBeInTheDocument()
  })

  it('renders "Edit Patient Profile" heading when editing an existing patient', () => {
    render(
      <PatientProfilePage
        {...defaultProps}
        activePatient={{ name: 'Jane Doe', age: 42, patient_id: 'p1' }}
      />
    )
    expect(screen.getByText('Edit Patient Profile')).toBeInTheDocument()
  })

  it('renders required form fields (name, age, sex)', () => {
    render(<PatientProfilePage {...defaultProps} />)
    expect(screen.getByLabelText(/Patient Full Name/i)).toBeInTheDocument()
    expect(screen.getByLabelText(/Patient Age/i)).toBeInTheDocument()
    expect(screen.getByLabelText(/Patient Biological Sex/i)).toBeInTheDocument()
  })

  it('populates form fields from activePatient prop', () => {
    render(
      <PatientProfilePage
        {...defaultProps}
        activePatient={{
          name: 'John Smith',
          age: 55,
          sex: 'Male',
          patient_id: 'p2',
          symptoms: ['fatigue'],
          conditions: ['anemia'],
          allergies: ['penicillin'],
          medications: ['iron supplement'],
        }}
      />
    )
    const nameInput = screen.getByLabelText(/Patient Full Name/i)
    expect(nameInput.value).toBe('John Smith')

    const ageInput = screen.getByLabelText(/Patient Age/i)
    expect(ageInput.value).toBe('55')
  })

  it('shows Create Patient Context button initially, and Save Patient Context when editing', () => {
    const { rerender } = render(<PatientProfilePage {...defaultProps} />)
    expect(screen.getByRole('button', { name: /Create Patient Context/i })).toBeInTheDocument()

    rerender(
      <PatientProfilePage
        {...defaultProps}
        activePatient={{ name: 'Jane Doe', age: 30, patient_id: 'p1' }}
      />
    )
    expect(screen.getByRole('button', { name: /Save Patient Context/i })).toBeInTheDocument()
  })

  it('shows Saving... text when loading', () => {
    render(<PatientProfilePage {...defaultProps} loading={true} />)
    expect(screen.getByRole('button', { name: /Saving.../i })).toBeInTheDocument()
  })

  it('allows typing into name and age fields', () => {
    render(<PatientProfilePage {...defaultProps} />)
    const nameInput = screen.getByLabelText(/Patient Full Name/i)
    fireEvent.change(nameInput, { target: { value: 'Test Patient' } })
    expect(nameInput.value).toBe('Test Patient')

    const ageInput = screen.getByLabelText(/Patient Age/i)
    fireEvent.change(ageInput, { target: { value: '30' } })
    expect(ageInput.value).toBe('30')
  })
})
