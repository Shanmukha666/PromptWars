import '@testing-library/jest-dom'
import { vi } from 'vitest'

// Mock DOM APIs not supported in jsdom
if (typeof window !== 'undefined') {
  window.HTMLElement.prototype.scrollIntoView = vi.fn()
  window.HTMLElement.prototype.scrollTo = vi.fn()
}
