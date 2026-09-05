/**
 * ReviewVerificationPage component tests:
 * - Renders observation details and grounding snippet
 * - Action buttons: Verify Correct, Edit Observation, Mark Incorrect
 * - Opens Edit Modal and verifies fields
 * - Displays Audit History & Provenance Log when audit trail exists
 */
import React from 'react'
import { render, screen, fireEvent, waitFor } from '@testing-library/react'
import { describe, it, expect, vi } from 'vitest'
import ReviewVerificationPage from '../components/ReviewVerificationPage'

describe('ReviewVerificationPage', () => {
  const mockDocument = {
    document_id: 'doc-123',
    title: 'Lab Report CBC',
    raw_text: 'Patient report text with Hemoglobin: 10.5 g/dL (Ref: 12.0 - 16.0)',
    extracted: {
      labs: {
        hemoglobin: {
          test_name: 'hemoglobin',
          display_name: 'Hemoglobin',
          value: 10.5,
          unit: 'g/dL',
          source_range_raw: '12.0 - 16.0 g/dL',
          reference_range: { min: 12.0, max: 16.0 },
          status: 'low',
          source_snippet: 'Hemoglobin: 10.5 g/dL (Ref: 12.0 - 16.0)',
          source_page: 1,
          provenance_type: 'source_extracted',
          verification_status: 'unverified',
          audit_trail: [
            {
              action: 'edit',
              original_value: 9.5,
              corrected_value: 10.5,
              changed_at: '2026-03-12T14:30:00Z',
              change_source: 'user_verified',
              notes: 'Corrected from second reading',
            },
          ],
        },
      },
    },
  }

  const defaultProps = {
    activePatient: {
      patient_id: 'p-1',
      name: 'Jane Doe',
      documents: [mockDocument],
    },
    activeDocument: mockDocument,
    onSelectDocument: vi.fn(),
    onVerifyOrEditLab: vi.fn().mockResolvedValue({}),
    onProceedToTimeline: vi.fn(),
    onNavigateStage: vi.fn(),
    loading: false,
  }

  it('renders observation value and source snippet', () => {
    render(<ReviewVerificationPage {...defaultProps} />)
    expect(screen.getAllByText(/10.5 g\/dL/i).length).toBeGreaterThan(0)
    expect(screen.getAllByText(/Hemoglobin: 10.5 g\/dL \(Ref: 12.0 - 16.0\)/i).length).toBeGreaterThan(0)
  })

  it('renders action buttons: Verify Correct, Edit Observation, Mark Incorrect', () => {
    render(<ReviewVerificationPage {...defaultProps} />)
    expect(screen.getByRole('button', { name: /Verify Correct/i })).toBeInTheDocument()
    expect(screen.getByRole('button', { name: /Edit Observation/i })).toBeInTheDocument()
    expect(screen.getByRole('button', { name: /Mark Incorrect/i })).toBeInTheDocument()
  })

  it('displays audit history when audit trail is present', () => {
    render(<ReviewVerificationPage {...defaultProps} />)
    expect(screen.getByText(/Audit History & Provenance Log/i)).toBeInTheDocument()
    expect(screen.getByText('EDIT')).toBeInTheDocument()
    expect(screen.getByText(/Corrected from second reading/i)).toBeInTheDocument()
  })

  it('opens edit modal when Edit Observation is clicked', () => {
    render(<ReviewVerificationPage {...defaultProps} />)
    const editBtn = screen.getByRole('button', { name: /Edit Observation/i })
    fireEvent.click(editBtn)

    expect(screen.getByText(/Edit Observation: HEMOGLOBIN/i)).toBeInTheDocument()
    expect(screen.getByRole('button', { name: /Save & Mark User-Verified/i })).toBeInTheDocument()
  })

  it('calls onVerifyOrEditLab when Verify Correct is clicked', async () => {
    const onVerifyOrEditLab = vi.fn().mockResolvedValue({})
    render(<ReviewVerificationPage {...defaultProps} onVerifyOrEditLab={onVerifyOrEditLab} />)

    const verifyBtn = screen.getByRole('button', { name: /Verify Correct/i })
    fireEvent.click(verifyBtn)

    await waitFor(() => {
      expect(onVerifyOrEditLab).toHaveBeenCalledWith(
        expect.objectContaining({
          document_id: 'doc-123',
          test_name: 'hemoglobin',
          action: 'verify',
        })
      )
    })
  })
})
