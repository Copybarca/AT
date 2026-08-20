import type { ReactNode } from 'react'
import { NavLink } from 'react-router'
import { useRealtime } from './RealtimeProvider'

const navigation = [
  { to: '/books', icon: 'pi pi-list', label: 'Список документов' },
  { to: '/books/new', icon: 'pi pi-plus', label: 'Загрузить' },
  { to: '/fragments', icon: 'pi pi-align-left', label: 'Фрагменты' },
  { to: '/build', icon: 'pi pi-file-export', label: 'Сборка' },
]

const realtimeLabels = {
  connected: 'Мониторинг подключён',
  connecting: 'Подключаем мониторинг…',
  disconnected: 'Ручное обновление',
} as const

export function AppShell({ children }: { children: ReactNode }) {
  const { status } = useRealtime()

  return (
    <div className="application-shell">
      <aside className="side-navigation">
        <div className="brand-block">
          <span className="brand-mark">AT</span>
          <span className="brand-copy"><strong>Перевод документов</strong><small>Рабочее пространство</small></span>
        </div>
        <nav aria-label="Основная навигация">
          {navigation.map((item) => (
            <NavLink key={item.to} to={item.to} className={({ isActive }) => `nav-item${isActive ? ' active' : ''}`}>
              <i className={item.icon} aria-hidden="true" />
              <span>{item.label}</span>
            </NavLink>
          ))}
        </nav>
      </aside>
      <section className="workspace">
        <header className="app-header">
          <span className="breadcrumbs">AT / Рабочее пространство</span>
          <span className={`realtime-status ${status}`}>
            <span className="realtime-dot" aria-hidden="true" />
            {realtimeLabels[status]}
          </span>
        </header>
        <main className="page-container">{children}</main>
      </section>
    </div>
  )
}
