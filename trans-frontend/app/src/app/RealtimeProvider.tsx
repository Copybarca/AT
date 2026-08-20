import { createContext, useContext, useEffect, useMemo, useState, type ReactNode } from 'react'

export type RealtimeStatus = 'connected' | 'connecting' | 'disconnected'

interface RealtimeContextValue {
  status: RealtimeStatus
  revision: number
}

const RealtimeContext = createContext<RealtimeContextValue>({ status: 'disconnected', revision: 0 })

export function RealtimeProvider({ children }: { children: ReactNode }) {
  const [status, setStatus] = useState<RealtimeStatus>('disconnected')
  const [revision, setRevision] = useState(0)

  useEffect(() => {
    const url = import.meta.env.VITE_WS_URL
    if (!url) return undefined
    let socket: WebSocket | null = null
    let reconnectTimer: number | undefined
    let stopped = false

    const connect = () => {
      if (stopped) return
      setStatus('connecting')
      socket = new WebSocket(url)
      socket.addEventListener('open', () => setStatus('connected'))
      socket.addEventListener('message', () => setRevision((value) => value + 1))
      socket.addEventListener('close', () => {
        setStatus('disconnected')
        if (!stopped) reconnectTimer = window.setTimeout(connect, 2500)
      })
      socket.addEventListener('error', () => socket?.close())
    }

    connect()
    return () => {
      stopped = true
      if (reconnectTimer) window.clearTimeout(reconnectTimer)
      socket?.close()
    }
  }, [])

  const value = useMemo(() => ({ status, revision }), [status, revision])
  return <RealtimeContext.Provider value={value}>{children}</RealtimeContext.Provider>
}

export const useRealtime = () => useContext(RealtimeContext)
