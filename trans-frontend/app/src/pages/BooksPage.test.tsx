import { render, screen } from '@testing-library/react'
import { MemoryRouter } from 'react-router'
import { afterEach, describe, expect, it, vi } from 'vitest'
import { RealtimeProvider } from '../app/RealtimeProvider'
import { ToastProvider } from '../app/ToastProvider'
import { BooksPage } from './BooksPage'

afterEach(() => vi.unstubAllGlobals())

describe('BooksPage', () => {
  it('renders clickable counters and factual backend data', async () => {
    vi.stubGlobal('fetch', vi.fn().mockResolvedValue(new Response(JSON.stringify({
      items: [{
        id: 7,
        title: 'Two-page English book',
        fileName: 'two-pages.pdf',
        sourceLanguage: 'eng',
        targetLanguage: 'rus',
        contentStatus: 'complete',
        translationStatus: 'completed',
        pdfStatus: 'ready',
        totalFragments: 12,
        translatedFragments: 12,
        imageCount: 1,
        updatedAt: '2026-08-20T12:00:00Z',
      }],
      counters: { all: 1, progress: 0, done: 1, failed: 0 },
    }), { status: 200, headers: { 'Content-Type': 'application/json' } })))

    render(
      <MemoryRouter>
        <ToastProvider>
          <RealtimeProvider>
            <BooksPage />
          </RealtimeProvider>
        </ToastProvider>
      </MemoryRouter>,
    )

    expect(await screen.findByText('Two-page English book')).toBeInTheDocument()
    expect(screen.getByRole('button', { name: /1 документа/ })).toBeInTheDocument()
    expect(screen.getByRole('textbox', { name: 'Поиск по названию' })).toBeInTheDocument()
  })
})
