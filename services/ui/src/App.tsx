import { useState, type FormEvent } from 'react'

type DemoResult = { demo: boolean; verdict: string; reason: string; idea: string }

declare global {
  interface Window { __CONFIG__?: { API_BASE: string } }
}

export default function App() {
  const [idea, setIdea] = useState('')
  const [result, setResult] = useState<DemoResult | null>(null)
  const [error, setError] = useState('')
  const [busy, setBusy] = useState(false)

  async function submit(event: FormEvent) {
    event.preventDefault()
    setBusy(true)
    setError('')
    setResult(null)
    try {
      const apiBase = window.__CONFIG__?.API_BASE ?? '/api'
      const response = await fetch(`${apiBase}/demo/validate`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ idea }),
      })
      if (!response.ok) throw new Error(`Request failed (${response.status})`)
      setResult(await response.json() as DemoResult)
    } catch (cause) {
      setError(cause instanceof Error ? cause.message : 'Request failed')
    } finally {
      setBusy(false)
    }
  }

  return <main>
    <p className="eyebrow">Idea Validator · Platform check</p>
    <h1>Go / No-Go</h1>
    <p>This Phase 2 demo checks the path through the UI, gateway, orchestrator and verdict service. It does not assess your idea yet.</p>
    <form onSubmit={submit}>
      <label htmlFor="idea">Your idea</label>
      <textarea id="idea" maxLength={500} required value={idea} onChange={event => setIdea(event.target.value)} />
      <button disabled={busy || !idea.trim()}>{busy ? 'Checking…' : 'Run demo'}</button>
    </form>
    {error && <p role="alert">{error}</p>}
    {result && <section aria-live="polite"><p className="eyebrow">Phase 2 demo result</p><h2>{result.verdict.replaceAll('_', ' ')}</h2><p>{result.reason}</p></section>}
  </main>
}
