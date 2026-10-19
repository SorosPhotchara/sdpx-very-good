import { useRef, useState } from 'react'

export function useAsyncLock() {
  const locked = useRef(false)
  const [busy, setBusy] = useState(false)
  function begin() {
    if (locked.current) return false
    locked.current = true
    setBusy(true)
    return true
  }
  function finish() {
    locked.current = false
    setBusy(false)
  }
  return { busy, begin, finish }
}
