import { render, screen } from '@testing-library/react'
import { MemoryRouter } from 'react-router'
import { beforeEach, describe, expect, it } from 'vitest'
import { RealtimeProvider } from '../app/RealtimeProvider'
import { ToastProvider } from '../app/ToastProvider'
import { resetDemoStateForTests } from '../services/bookService'
import { BooksPage } from './BooksPage'

describe('BooksPage', () => {
  beforeEach(() => resetDemoStateForTests())

  it('renders clickable counters and document data', async () => {
    render(
      <MemoryRouter>
        <ToastProvider>
          <RealtimeProvider>
            <BooksPage />
          </RealtimeProvider>
        </ToastProvider>
      </MemoryRouter>,
    )

    expect(await screen.findByText('Designing Data-Intensive Applications')).toBeInTheDocument()
    expect(screen.getByRole('button', { name: /5 документа/ })).toBeInTheDocument()
    expect(screen.getByRole('textbox', { name: 'Поиск по названию' })).toBeInTheDocument()
  })
})
