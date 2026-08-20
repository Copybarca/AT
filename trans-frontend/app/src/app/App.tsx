import { lazy, Suspense } from 'react'
import { Navigate, Route, Routes } from 'react-router'
import { AppShell } from './AppShell'
import { RealtimeProvider } from './RealtimeProvider'
import { ToastProvider } from './ToastProvider'

const BooksPage = lazy(() => import('../pages/BooksPage').then((module) => ({ default: module.BooksPage })))
const UploadPage = lazy(() => import('../pages/UploadPage').then((module) => ({ default: module.UploadPage })))
const BookDetailPage = lazy(() => import('../pages/BookDetailPage').then((module) => ({ default: module.BookDetailPage })))
const FragmentLandingPage = lazy(() => import('../pages/FragmentLandingPage').then((module) => ({ default: module.FragmentLandingPage })))
const FragmentsPage = lazy(() => import('../pages/FragmentsPage').then((module) => ({ default: module.FragmentsPage })))
const BuildPage = lazy(() => import('../pages/BuildPage').then((module) => ({ default: module.BuildPage })))

export function App() {
  return (
    <ToastProvider>
      <RealtimeProvider>
        <AppShell>
          <Suspense fallback={<div className="page-loading"><i className="pi pi-spin pi-spinner" /> Загружаем страницу…</div>}>
            <Routes>
              <Route path="/books" element={<BooksPage />} />
              <Route path="/books/new" element={<UploadPage />} />
              <Route path="/books/:bookId" element={<BookDetailPage />} />
              <Route path="/fragments" element={<FragmentLandingPage />} />
              <Route path="/books/:bookId/fragments" element={<FragmentsPage />} />
              <Route path="/build" element={<BuildPage />} />
              <Route path="/" element={<Navigate replace to="/books" />} />
              <Route path="*" element={<Navigate replace to="/books" />} />
            </Routes>
          </Suspense>
        </AppShell>
      </RealtimeProvider>
    </ToastProvider>
  )
}
