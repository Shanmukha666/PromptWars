/**
 * WorkflowStates component tests:
 * - Empty document & observations state
 * - Filter criteria producing no match
 * - Loading indicator state in forms
 */
import React from 'react'
import { render, screen, fireEvent } from '@testing-library/react'
import { describe, it, expect, vi } from 'vitest'
import StructuredRecordPage from '../components/StructuredRecordPage'
import PatientProfilePage from '../components/PatientProfilePage'

describe('Workflow Empty & Loading States', () => {
  it('renders empty observations placeholder when no documents or labs exist', () => {
    const emptyPatient = {
      patient_id: 'p-empty',
      name: 'Empty Patient',
      documents: [],
    }

    render(
      <StructuredRecordPage
        activePatient={emptyPatient}
        activeDocument={null}
        onSelectDocument={vi.fn()}
        onProceedToReview={vi.fn()}
        onProceedToTimeline={vi.fn()}
        onNavigateStage={vi.fn()}
      />
    )

    expect(screen.getByText('No structured observations available')).toBeInTheDocument()
    expect(
      screen.getByText(/No laboratory observations have been extracted yet/i)
    ).toBeInTheDocument()
  })

  it('renders "no matches" placeholder when search filters out all observations', () => {
    const patientWithDoc = {
      patient_id: 'p-1',
      name: 'Patient One',
      documents: [
        {
          document_id: 'd-1',
          title: 'CBC',
          extracted: {
            labs: {
              hemoglobin: {
                test_name: 'hemoglobin',
                display_name: 'Hemoglobin',
                value: 14.0,
                unit: 'g/dL',
                reference_range: { min: 12.0, max: 16.0 },
                status: 'normal',
              },
            },
          },
        },
      ],
    }

    render(
      <StructuredRecordPage
        activePatient={patientWithDoc}
        activeDocument={patientWithDoc.documents[0]}
        onSelectDocument={vi.fn()}
        onProceedToReview={vi.fn()}
        onProceedToTimeline={vi.fn()}
        onNavigateStage={vi.fn()}
      />
    )

    const searchInput = screen.getByLabelText(/Search observations/i)
    fireEvent.change(searchInput, { target: { value: 'nonexistent-query-xyz' } })

    expect(
      screen.getByText(/No clinical observations match the selected search and filter criteria/i)
    ).toBeInTheDocument()
  })

  it('displays loading state on patient form submit button when loading is true', () => {
    render(
      <PatientProfilePage
        activePatient={null}
        onSavePatient={vi.fn()}
        onProceedToReports={vi.fn()}
        loading={true}
      />
    )

    const saveButton = screen.getByRole('button', { name: /Saving.../i })
    expect(saveButton).toBeInTheDocument()
    expect(saveButton).toBeDisabled()
  })
})
