import { createContext, useContext, useMemo, useRef, type ReactNode } from 'react'
import { Toast } from 'primereact/toast'

interface ToastMessageApi {
  success: (summary: string, detail: string) => void
  error: (summary: string, detail: string) => void
  info: (summary: string, detail: string) => void
}

const ToastContext = createContext<ToastMessageApi | null>(null)

export function ToastProvider({ children }: { children: ReactNode }) {
  const toastRef = useRef<Toast>(null)
  const value = useMemo<ToastMessageApi>(() => ({
    success: (summary, detail) => toastRef.current?.show({ severity: 'success', summary, detail, life: 3500 }),
    error: (summary, detail) => toastRef.current?.show({ severity: 'error', summary, detail, life: 5000 }),
    info: (summary, detail) => toastRef.current?.show({ severity: 'info', summary, detail, life: 3500 }),
  }), [])

  return (
    <ToastContext.Provider value={value}>
      <Toast ref={toastRef} position="bottom-right" />
      {children}
    </ToastContext.Provider>
  )
}

export function useToastMessage(): ToastMessageApi {
  const context = useContext(ToastContext)
  if (!context) throw new Error('useToastMessage must be used inside ToastProvider')
  return context
}
