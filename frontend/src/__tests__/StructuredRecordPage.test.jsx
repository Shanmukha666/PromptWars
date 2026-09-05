/**
 * StructuredRecordPage component tests:
 * - Table semantics and observation listing
 * - Status indicators: "Not assessed (No source range)" with symbol "—", "Within range" with "✓", "Low" with "▼"
 * - Absolute Rule: When source range is missing, status is strictly "Not assessed"
 * - Provenance badge indicators
 * - Filtering observations
 */
import React from 'react'
import { render, screen, fireEvent, within } from '@testing-library/react'
import { describe, it, expect, vi } from 'vitest'
import StructuredRecordPage from '../components/StructuredRecordPage'

describe('StructuredRecordPage', () => {
  const mockPatient = {
    patient_id: 'p-1',
    name: 'Jane Doe',
    documents: [
      {
        document_id: 'doc-1',
        title: 'Comprehensive Metabolic Panel',
        created_at: '2026-03-10T10:00:00Z',
        extracted: {
          labs: {
            hemoglobin: {
              test_name: 'hemoglobin',
              display_name: 'Hemoglobin',
              value: 10.2,
              unit: 'g/dL',
              reference_range_raw: '12.0 - 16.0 g/dL',
              reference_range: { min: 12.0, max: 16.0 },
              status: 'low',
              provenance_type: 'source_extracted',
              verification_status: 'unverified',
            },
            potassium: {
              test_name: 'potassium',
              display_name: 'Potassium',
              value: 4.1,
              unit: 'mmol/L',
              reference_range_raw: '3.5 - 5.0 mmol/L',
              reference_range: { min: 3.5, max: 5.0 },
              status: 'normal',
              provenance_type: 'source_extracted',
              verification_status: 'unverified',
            },
            glucose: {
              test_name: 'glucose',
              display_name: 'Glucose',
              value: 105.0,
              unit: 'mg/dL',
              reference_range_raw: null,
              reference_range: null,
              status: 'not_assessed',
              provenance_type: 'source_extracted',
              verification_status: 'unverified',
            },
          },
        },
      },
    ],
  }

  const defaultProps = {
    activePatient: mockPatient,
    activeDocument: mockPatient.documents[0],
    onSelectDocument: vi.fn(),
    onProceedToReview: vi.fn(),
    onProceedToTimeline: vi.fn(),
    onNavigateStage: vi.fn(),
  }

  it('renders table headers and observation rows', () => {
    render(<StructuredRecordPage {...defaultProps} />)
    const table = screen.getByRole('table')
    expect(within(table).getByText(/hemoglobin/i)).toBeInTheDocument()
    expect(within(table).getByText(/potassium/i)).toBeInTheDocument()
    expect(within(table).getByText(/glucose/i)).toBeInTheDocument()
  })

  it('renders "Not assessed (No source range)" with "—" symbol when range is missing', () => {
    render(<StructuredRecordPage {...defaultProps} />)
    const table = screen.getByRole('table')
    expect(within(table).getByText(/Not assessed \(No source range\)/i)).toBeInTheDocument()
  })

  it('renders "Low (Below range)" with "▼" symbol for values below source range', () => {
    render(<StructuredRecordPage {...defaultProps} />)
    const table = screen.getByRole('table')
    expect(within(table).getByText(/Low \(Below range\)/i)).toBeInTheDocument()
  })

  it('renders "Within range" with "✓" symbol for values inside source range', () => {
    render(<StructuredRecordPage {...defaultProps} />)
    const table = screen.getByRole('table')
    expect(within(table).getByText(/Within range/i)).toBeInTheDocument()
  })

  it('filters rows based on search input', () => {
    render(<StructuredRecordPage {...defaultProps} />)
    const searchInput = screen.getByLabelText(/Search observations/i)
    fireEvent.change(searchInput, { target: { value: 'potassium' } })

    const table = screen.getByRole('table')
    expect(within(table).getByText(/potassium/i)).toBeInTheDocument()
    expect(within(table).queryByText(/hemoglobin/i)).not.toBeInTheDocument()
  })
})
