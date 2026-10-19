import { useEffect, useState } from 'react'
import type { Language } from './i18n'

// Ticks once a second so an evaluation page can count down to its deadline.
// Returns the remaining milliseconds, clamped at zero, or null when no deadline is set.
export function useCountdown(deadline: string | null): number | null {
  const target = deadline ? new Date(deadline).getTime() : null
  const valid = target != null && !Number.isNaN(target)
  const [now, setNow] = useState(() => Date.now())

  useEffect(() => {
    if (!valid) return
    setNow(Date.now())
    const timer = setInterval(() => setNow(Date.now()), 1000)
    return () => clearInterval(timer)
  }, [valid, target])

  if (!valid) return null
  return Math.max(0, target - now)
}

export function formatCountdown(remaining: number, language: Language): string {
  const total = Math.floor(remaining / 1000)
  const days = Math.floor(total / 86400)
  const hours = Math.floor((total % 86400) / 3600)
  const minutes = Math.floor((total % 3600) / 60)
  const seconds = total % 60
  const units = language === 'th'
    ? { day: ' วัน', hour: ' ชม.', minute: ' นาที', second: ' วินาที' }
    : { day: 'd', hour: 'h', minute: 'm', second: 's' }
  // Drop the smallest unit once the remaining time is large enough to make it noise.
  const parts = days > 0
    ? [`${days}${units.day}`, `${hours}${units.hour}`, `${minutes}${units.minute}`]
    : hours > 0
      ? [`${hours}${units.hour}`, `${minutes}${units.minute}`]
      : [`${minutes}${units.minute}`, `${seconds}${units.second}`]
  return parts.join(' ')
}
