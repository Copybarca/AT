import { useCallback, useEffect, useState } from 'react'
import { useNavigate, useParams } from 'react-router'
import { Button } from 'primereact/button'
import { Message } from 'primereact/message'
import { ProgressBar } from 'primereact/progressbar'
import type { Book } from '../domain/types'
import { bookService } from '../services/bookService'
import { PdfStatusTag, TranslationStatusTag } from '../shared/StatusTag'

export function BookDetailPage() {
  const navigate = useNavigate()
  const { bookId } = useParams()
  const numericBookId = Number(bookId)
  const [book, setBook] = useState<Book | null>(null)
  const [error, setError] = useState<string | null>(null)

  const loadBook = useCallback(() => bookService.getBook(numericBookId).then(setBook), [numericBookId])

  useEffect(() => {
    void loadBook().catch((reason: unknown) => {
      setError(reason instanceof Error ? reason.message : 'Не удалось загрузить книгу')
    })
  }, [loadBook])

  useEffect(() => {
    if (!book || book.pdfStatus === 'ready' || book.pdfStatus === 'failed') return undefined
    const timer = window.setInterval(() => void loadBook(), 2500)
    return () => window.clearInterval(timer)
  }, [book, loadBook])

  if (error) return <Message severity="error" text={error} className="wide-message" />
  if (!book) return <div className="page-loading"><i className="pi pi-spin pi-spinner" /> Загружаем книгу…</div>

  const percent = book.totalFragments ? Math.round(book.translatedFragments / book.totalFragments * 100) : 0

  return (
    <section>
      <div className="page-heading">
        <div>
          <Button label="К списку" icon="pi pi-arrow-left" text onClick={() => navigate('/books')} />
          <h1>{book.title}</h1>
          <p>Книга #{book.id} · {book.fileName}</p>
        </div>
        <div className="heading-actions">
          <Button label="Ручной перевод" icon="pi pi-align-left" outlined onClick={() => navigate(`/books/${book.id}/fragments`)} />
          <Button label="Сборка" icon="pi pi-file-export" onClick={() => navigate('/build', { state: { bookId: book.id } })} />
          {book.pdfStatus === 'ready' && book.targetLanguage && <Button label="Скачать PDF" icon="pi pi-download" onClick={() => { window.location.href = bookService.translatedPdfUrl(book.id, book.targetLanguage ?? '') }} />}
        </div>
      </div>

      <div className="detail-facts">
        <article><small>Контент</small><strong>{book.contentStatus === 'complete' ? 'Загружен полностью' : book.contentStatus === 'failed' ? 'Ошибка извлечения' : 'Загружается'}</strong></article>
        <article><small>База переводов</small><TranslationStatusTag status={book.translationStatus} /></article>
        <article><small>Итоговый документ</small><PdfStatusTag status={book.pdfStatus} /></article>
        <article><small>Языки</small><strong>{book.sourceLanguage} → {book.targetLanguage ?? '—'}</strong></article>
      </div>

      <div className="pipeline-card">
        <div className="pipeline-heading"><h2>Обработка</h2><strong>{percent}%</strong></div>
        <ProgressBar value={percent} />
        <div className="pipeline-steps">
          <div className={`pipeline-step ${book.contentStatus === 'complete' ? 'complete' : book.contentStatus === 'uploading' ? 'active' : ''}`}><i className={book.contentStatus === 'complete' ? 'pi pi-check' : 'pi pi-file-import'} /><span><strong>1. Извлечение</strong><small>{book.totalFragments} фрагментов · {book.imageCount} изображений</small></span></div>
          <div className={`pipeline-step ${book.translationStatus === 'completed' ? 'complete' : book.translationStatus === 'in_progress' ? 'active' : ''}`}><i className={book.translationStatus === 'completed' ? 'pi pi-check' : 'pi pi-language'} /><span><strong>2. Перевод</strong><small>{book.translatedFragments} / {book.totalFragments} сохранено в базе</small></span></div>
          <div className={`pipeline-step ${book.pdfStatus === 'ready' ? 'complete' : book.pdfStatus === 'building' ? 'active' : ''}`}><i className={book.pdfStatus === 'ready' ? 'pi pi-check' : 'pi pi-file-pdf'} /><span><strong>3. Итоговый PDF</strong><small>{book.pdfStatus === 'ready' ? 'Готов к выгрузке' : 'Не собран'}</small></span></div>
        </div>
      </div>
    </section>
  )
}
