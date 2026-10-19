import { useCallback, useEffect, useRef, useState, type SetStateAction } from 'react'

export function useResource<T>(key: string, load: () => Promise<T>, enabled = true) {
  const loader = useRef(load)
  const currentKey = useRef(key)
  const revision = useRef(0)
  const pending = useRef<{ key: string; promise: Promise<T> } | null>(null)
  loader.current = load
  currentKey.current = key
  const [state, setState] = useState<{ key: string; data: T | null; loading: boolean; error: string }>({ key, data: null, loading: enabled, error: '' })
  const refresh = useCallback(async (force = true) => {
    const request = ++revision.current
    setState((previous) => ({ key, data: previous.key === key ? previous.data : null, loading: true, error: '' }))
    try {
      const promise = !force && pending.current?.key === key ? pending.current.promise : loader.current()
      pending.current = { key, promise }
      const data = await promise
      if (request === revision.current && currentKey.current === key) setState({ key, data, loading: false, error: '' })
    } catch (problem) {
      if (request === revision.current && currentKey.current === key) setState((previous) => ({ ...previous, loading: false, error: problem instanceof Error ? problem.message : 'Could not load data.' }))
    }
  }, [key])
  const setData = useCallback((update: SetStateAction<T | null>) => {
    if (currentKey.current !== key) return
    revision.current += 1
    setState((previous) => ({ key, data: typeof update === 'function' ? (update as (data: T | null) => T | null)(previous.key === key ? previous.data : null) : update, loading: false, error: '' }))
  }, [key])
  useEffect(() => {
    if (enabled) void refresh(false)
    return () => { revision.current += 1 }
  }, [enabled, refresh])
  return { data: state.key === key ? state.data : null, loading: state.key === key ? state.loading : enabled, error: state.key === key ? state.error : '', refresh, setData }
}
