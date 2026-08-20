import { useEffect, useState } from 'react'
import { useNavigate } from 'react-router'
import { Button } from 'primereact/button'
import { Dropdown } from 'primereact/dropdown'
import { Message } from 'primereact/message'
import type { Book } from '../domain/types'
import { bookService } from '../services/bookService'

export function FragmentLandingPage() {
  const navigate = useNavigate()
  const [books, setBooks] = useState<Book[]>([])
  const [selectedBookId, setSelectedBookId] = useState<number | null>(null)
  const [error, setError] = useState<string | null>(null)

  useEffect(() => {
    void bookService.listContentCompleteBooks().then(setBooks).catch((reason: unknown) => {
      setError(reason instanceof Error ? reason.message : 'Не удалось получить список книг')
    })
  }, [])

  return (
    <section>
      <div className="page-heading"><div><h1>Ручной перевод фрагментов</h1><p>Сначала выберите конкретную книгу из списка, полученного сервисом.</p></div></div>
      {error && <Message severity="error" text={error} className="wide-message" />}
      <div className="selection-card">
        <label htmlFor="fragment-book">Книга</label>
        <Dropdown
          inputId="fragment-book"
          value={selectedBookId}
          options={books}
          optionLabel="title"
          optionValue="id"
          filter
          filterBy="title"
          placeholder="Выберите книгу"
          onChange={(event) => setSelectedBookId(event.value as number)}
          itemTemplate={(book: Book) => <div><strong>{book.title}</strong><small className="table-subtitle">Книга #{book.id}</small></div>}
          valueTemplate={(book?: Book) => book ? `${book.title} · #${book.id}` : 'Выберите книгу'}
        />
        <Button label="Показать фрагменты" icon="pi pi-arrow-right" iconPos="right" disabled={!selectedBookId} onClick={() => navigate(`/books/${selectedBookId}/fragments`)} />
      </div>
    </section>
  )
}
