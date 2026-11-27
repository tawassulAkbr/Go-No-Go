import { fireEvent, render, screen, waitFor } from '@testing-library/react'
import { afterEach, expect, test, vi } from 'vitest'
import App from './App'

afterEach(() => vi.restoreAllMocks())

test('submits a demo idea through the gateway and labels the result', async () => {
  const fetchMock = vi.spyOn(globalThis, 'fetch').mockResolvedValue({
    ok: true,
    json: async () => ({
      demo: true,
      verdict: 'INSUFFICIENT_EVIDENCE',
      reason: 'No evidence has been collected.',
      idea: 'A study planner',
    }),
  } as Response)

  render(<App />)
  fireEvent.change(screen.getByLabelText('Your idea'), { target: { value: 'A study planner' } })
  fireEvent.click(screen.getByRole('button', { name: 'Run demo' }))

  await waitFor(() => expect(screen.getByText('INSUFFICIENT EVIDENCE')).toBeTruthy())
  expect(screen.getByText('Phase 2 demo result')).toBeTruthy()
  expect(fetchMock).toHaveBeenCalledWith('/api/demo/validate', expect.objectContaining({ method: 'POST' }))
})
