import { useCallback, useEffect, useState } from 'react'
import { useNavigate } from 'react-router'
import { Button } from 'primereact/button'
import { Column } from 'primereact/column'
import { DataTable } from 'primereact/datatable'
import { InputText } from 'primereact/inputtext'
import { Message } from 'primereact/message'
import { ProgressBar } from 'primereact/progressbar'
import type { Book, BookCounters, BookStatusFilter } from '../domain/types'
import { useRealtime } from '../app/RealtimeProvider'
import { bookService } from '../services/bookService'
import { BookMainStatusTag } from '../shared/StatusTag'

const filters: Array<{ value: BookStatusFilter; label: string; counter: keyof BookCounters }> = [
  { value: 'all', label: 'документа', counter: 'all' },
  { value: 'progress', label: 'переводятся', counter: 'progress' },
  { value: 'done', label: 'готовы', counter: 'done' },
  { value: 'failed', label: 'с ошибкой', counter: 'failed' },
]

export function BooksPage() {
  const navigate = useNavigate()
  const { revision } = useRealtime()
  const [books, setBooks] = useState<Book[]>([])
  const [counters, setCounters] = useState<BookCounters>({ all: 0, progress: 0, done: 0, failed: 0 })
  const [filter, setFilter] = useState<BookStatusFilter>('all')
  const [search, setSearch] = useState('')
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState<string | null>(null)

  const loadBooks = useCallback(async () => {
    setLoading(true)
    setError(null)
    try {
      const result = await bookService.listBooks(search, filter)
      setBooks(result.items)
      setCounters(result.counters)
    } catch (reason) {
      setError(reason instanceof Error ? reason.message : 'Не удалось загрузить документы')
    } finally {
      setLoading(false)
    }
  }, [filter, search])

  useEffect(() => {
    const timer = window.setTimeout(() => void loadBooks(), 220)
    return () => window.clearTimeout(timer)
  }, [loadBooks, revision])

  const titleBody = (book: Book) => (
    <div>
      <strong className="table-title">{book.title}</strong>
      <small className="table-subtitle">Книга #{book.id} · {book.fileName}</small>
    </div>
  )

  const progressBody = (book: Book) => {
    if (!book.totalFragments) return 'Ожидаем извлечение'
    const percent = Math.round((book.translatedFragments / book.totalFragments) * 100)
    return (
      <div className="table-progress">
        <span>{percent}% · {book.translatedFragments} / {book.totalFragments}</span>
        <ProgressBar value={percent} showValue={false} />
      </div>
    )
  }

  return (
    <section>
      <div className="page-heading">
        <div><h1>Документы</h1><p>Загрузка, перевод, ручная редактура и сборка итогового PDF.</p></div>
        <Button label="Загрузить файлы" icon="pi pi-plus" onClick={() => navigate('/books/new')} />
      </div>

      <div className="metric-filters" role="group" aria-label="Фильтр документов по состоянию">
        {filters.map((item) => (
          <button
            key={item.value}
            type="button"
            className={`metric-button${filter === item.value ? ' active' : ''}`}
            aria-pressed={filter === item.value}
            onClick={() => setFilter(item.value)}
          >
            <strong>{counters[item.counter]}</strong> {item.label}
          </button>
        ))}
      </div>

      <div className="content-panel">
        <div className="panel-toolbar">
          <span className="p-input-icon-left search-field">
            <i className="pi pi-search" />
            <InputText value={search} onChange={(event) => setSearch(event.target.value)} placeholder="Поиск по названию" aria-label="Поиск по названию" />
          </span>
          <Button label="Обновить" icon="pi pi-refresh" outlined onClick={() => void loadBooks()} />
        </div>
        {error && <Message severity="error" text={error} className="wide-message" />}
        <DataTable
          value={books}
          loading={loading}
          dataKey="id"
          emptyMessage="Документы не найдены"
          stripedRows
          rowHover
          onRowClick={(event) => navigate(`/books/${event.data.id}`)}
          tableStyle={{ minWidth: '840px' }}
        >
          <Column header="Документ" body={titleBody} />
          <Column header="Языки" body={(book: Book) => `${book.sourceLanguage} → ${book.targetLanguage}`} />
          <Column header="Состояние" body={(book: Book) => <BookMainStatusTag book={book} />} />
          <Column header="Прогресс" body={progressBody} />
          <Column
            header=""
            body={(book: Book) => <Button label="Открыть" icon="pi pi-arrow-right" iconPos="right" text onClick={(event) => { event.stopPropagation(); navigate(`/books/${book.id}`) }} />}
          />
        </DataTable>
      </div>
    </section>
  )
}
