const API_BASE = import.meta.env.VITE_API_BASE_URL || 'http://localhost:8000'
const REQUEST_TIMEOUT_MS = 15000

export async function request(path, options = {}) {
  const controller = new AbortController()
  const timeoutId = window.setTimeout(() => controller.abort(), REQUEST_TIMEOUT_MS)

  try {
    const response = await fetch(`${API_BASE}${path}`, { ...options, signal: controller.signal })
    if (!response.ok) {
      const message = await response.text()
      throw new Error(message || `Request failed: ${response.status}`)
    }
    return response.json()
  } catch (error) {
    if (error.name === 'AbortError') {
      throw new Error('The clinical service took too long to respond. Please try again.')
    }
    throw error
  } finally {
    window.clearTimeout(timeoutId)
  }
}
