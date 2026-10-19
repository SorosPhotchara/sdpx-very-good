import { ChevronRight } from 'lucide-react'
import type { ComponentPropsWithoutRef } from 'react'

import { cn } from '@/lib/utils'

export function DisclosureSummary({ children, className, ...props }: ComponentPropsWithoutRef<'summary'>) {
  return <summary className={cn('app-disclosure-summary cursor-pointer', className)} {...props}>
    <ChevronRight aria-hidden="true" size={16} strokeWidth={2.25} />
    {children}
  </summary>
}
