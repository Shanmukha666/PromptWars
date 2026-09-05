/**
 * ReportsPage component tests:
 * - Renders upload UI (headers, tabs, notice banner)
 * - File selection and drag-drop area
 * - Switches between File Upload and Paste Text tabs
 * - Validates text input (button disabled when empty)
 * - Submits text reports
 */
import React from 'react'
import { render, screen, fireEvent, waitFor } from '@testing-library/react'
import { describe, it, expect, vi } from 'vitest'
import ReportsPage from '../components/ReportsPage'

describe('ReportsPage', () => {
  const defaultProps = {
    activePatient: { name: 'Alex Johnson', patient_id: 'p123' },
    activeDocument: null,
    onUploadFile: vi.fn(),
    onUploadText: vi.fn().mockResolvedValue({}),
    onSelectDocument: vi.fn(),
    onProceedToStructured: vi.fn(),
    loading: false,
  }

  it('renders page header and health data warning notice', () => {
    render(<ReportsPage {...defaultProps} />)
    expect(screen.getByText('Upload medical reports')).toBeInTheDocument()
    expect(screen.getByText(/Health Data Notice/i)).toBeInTheDocument()
  })

  it('renders tab buttons to switch between file and text input', () => {
    render(<ReportsPage {...defaultProps} />)
    expect(screen.getByRole('button', { name: /File Upload/i })).toBeInTheDocument()
    expect(screen.getByRole('button', { name: /Paste Report Text/i })).toBeInTheDocument()
  })

  it('shows file upload dropzone by default', () => {
    render(<ReportsPage {...defaultProps} />)
    const fileInput = screen.getByLabelText(/Upload clinical report files/i)
    expect(fileInput).toBeInTheDocument()
    expect(fileInput).toHaveAttribute('type', 'file')
  })

  it('switches to paste text mode and renders textarea', () => {
    render(<ReportsPage {...defaultProps} />)
    const pasteTab = screen.getByRole('button', { name: /Paste Report Text/i })
    fireEvent.click(pasteTab)

    expect(screen.getByPlaceholderText(/Paste clinical laboratory report text/i)).toBeInTheDocument()
    expect(screen.getByRole('button', { name: /Process & Index Report/i })).toBeInTheDocument()
  })

  it('disables submit button when report text is empty', () => {
    render(<ReportsPage {...defaultProps} />)
    const pasteTab = screen.getByRole('button', { name: /Paste Report Text/i })
    fireEvent.click(pasteTab)

    const submitBtn = screen.getByRole('button', { name: /Process & Index Report/i })
    expect(submitBtn).toBeDisabled()
  })

  it('calls onUploadText when valid text is submitted', async () => {
    const onUploadText = vi.fn().mockResolvedValue({})
    render(<ReportsPage {...defaultProps} onUploadText={onUploadText} />)

    fireEvent.click(screen.getByRole('button', { name: /Paste Report Text/i }))
    const textarea = screen.getByPlaceholderText(/Paste clinical laboratory report text/i)
    fireEvent.change(textarea, { target: { value: 'Hemoglobin: 13.5 g/dL (Ref: 12.0 - 16.0)' } })

    const submitBtn = screen.getByRole('button', { name: /Process & Index Report/i })
    expect(submitBtn).not.toBeDisabled()
    fireEvent.click(submitBtn)

    await waitFor(() => {
      expect(onUploadText).toHaveBeenCalledWith(
        'Hemoglobin: 13.5 g/dL (Ref: 12.0 - 16.0)',
        'Pasted Clinical Report'
      )
    })
  })
})
