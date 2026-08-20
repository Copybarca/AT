import { useCallback, useEffect, useRef, useState } from 'react'
import { useNavigate, useParams } from 'react-router'
import { Button } from 'primereact/button'
import { InputTextarea } from 'primereact/inputtextarea'
import { Message } from 'primereact/message'
import { SelectButton } from 'primereact/selectbutton'
import { Tag } from 'primereact/tag'
import { useToastMessage } from '../app/ToastProvider'
import type { Book, Fragment, FragmentFilter } from '../domain/types'
import { bookService } from '../services/bookService'

const filterOptions = [
  { label: 'Все фрагменты', value: 'all' },
  { label: 'Только непереведённые', value: 'untranslated' },
]

function FragmentEditor({ fragment, onSaved }: { fragment: Fragment; onSaved: (fragment: Fragment) => void }) {
  const toast = useToastMessage()
  const [translation, setTranslation] = useState(fragment.translatedText ?? '')
  const [saving, setSaving] = useState(false)

  const save = async () => {
    if (!translation.trim()) {
      toast.error('Перевод не сохранён', 'Введите текст перевода.')
      return
    }
    setSaving(true)
    try {
      const saved = await bookService.saveFragmentTranslation(fragment.bookId, fragment.id, translation)
      onSaved(saved)
      toast.success('Перевод сохранён', `Фрагмент sequence ${fragment.sequence} обновлён.`)
    } catch (reason) {
      toast.error('Не удалось сохранить перевод', reason instanceof Error ? reason.message : 'Повторите попытку')
    } finally {
      setSaving(false)
    }
  }

  return (
    <article className="fragment-card">
      <header><strong>sequence {fragment.sequence}</strong><Tag severity={fragment.translatedText ? 'success' : 'secondary'} value={fragment.translatedText ? 'ПЕРЕВЕДЁН' : 'НЕ ПЕРЕВЕДЁН'} /></header>
      <div className="fragment-columns">
        <div className="fragment-pane">
          <label htmlFor={`translation-${fragment.id}`}>Перевод</label>
          <InputTextarea id={`translation-${fragment.id}`} value={translation} onChange={(event) => setTranslation(event.target.value)} rows={6} autoResize />
        </div>
        <div className="fragment-pane original-pane"><span>Оригинал</span><p>{fragment.originalText}</p></div>
      </div>
      <footer><small>Сохраняется отдельно для этого фрагмента</small><Button label="Сохранить перевод" icon={saving ? 'pi pi-spin pi-spinner' : 'pi pi-save'} disabled={saving} onClick={() => void save()} /></footer>
    </article>
  )
}

export function FragmentsPage() {
  const navigate = useNavigate()
  const { bookId } = useParams()
  const numericBookId = Number(bookId)
  const [book, setBook] = useState<Book | null>(null)
  const [filter, setFilter] = useState<FragmentFilter>('all')
  const [fragments, setFragments] = useState<Fragment[]>([])
  const [loading, setLoading] = useState(false)
  const [error, setError] = useState<string | null>(null)
  const cursorRef = useRef<number | null>(null)
  const hasMoreRef = useRef(true)
  const loadingRef = useRef(false)
  const sentinelRef = useRef<HTMLDivElement>(null)
  const generationRef = useRef(0)

  useEffect(() => {
    void bookService.getBook(numericBookId).then(setBook).catch((reason: unknown) => {
      setError(reason instanceof Error ? reason.message : 'Не удалось получить книгу')
    })
  }, [numericBookId])

  const loadMore = useCallback(async (reset = false) => {
    if (loadingRef.current || (!reset && !hasMoreRef.current)) return
    loadingRef.current = true
    setLoading(true)
    const generation = generationRef.current
    try {
      const page = await bookService.getFragments({
        bookId: numericBookId,
        afterSequence: reset ? null : cursorRef.current,
        limit: 6,
        filter,
      })
      if (generation !== generationRef.current) return
      setFragments((current) => {
        const items = reset ? page.items : [...current, ...page.items]
        return items.sort((left, right) => left.sequence - right.sequence)
      })
      cursorRef.current = page.nextSequence
      hasMoreRef.current = page.nextSequence != null
    } catch (reason) {
      setError(reason instanceof Error ? reason.message : 'Не удалось загрузить фрагменты')
    } finally {
      loadingRef.current = false
      setLoading(false)
    }
  }, [filter, numericBookId])

  useEffect(() => {
    generationRef.current += 1
    cursorRef.current = null
    hasMoreRef.current = true
    loadingRef.current = false
    setFragments([])
    setError(null)
    void loadMore(true)
  }, [loadMore])

  useEffect(() => {
    const sentinel = sentinelRef.current
    if (!sentinel) return undefined
    const observer = new IntersectionObserver((entries) => {
      if (entries.some((entry) => entry.isIntersecting)) void loadMore()
    }, { rootMargin: '180px 0px' })
    observer.observe(sentinel)
    return () => observer.disconnect()
  }, [loadMore])

  const saved = (updated: Fragment) => {
    if (filter === 'untranslated') {
      setFragments((current) => current.filter((fragment) => fragment.id !== updated.id))
      void loadMore()
    } else {
      setFragments((current) => current.map((fragment) => fragment.id === updated.id ? updated : fragment))
    }
  }

  return (
    <section>
      <div className="page-heading">
        <div><h1>Ручной перевод фрагментов</h1><p>{book ? `${book.title} · книга #${book.id}` : `Книга #${numericBookId}`} · порядок строго по sequence.</p></div>
        <Button label="К документу" icon="pi pi-arrow-left" outlined onClick={() => navigate(`/books/${numericBookId}`)} />
      </div>
      <div className="fragment-toolbar">
        <SelectButton value={filter} options={filterOptions} onChange={(event) => event.value && setFilter(event.value as FragmentFilter)} allowEmpty={false} />
        <span><strong>{fragments.length}</strong> показано · следующая порция загрузится автоматически</span>
      </div>
      {error && <Message severity="error" text={error} className="wide-message" />}
      <div className="fragment-list">
        {fragments.map((fragment) => <FragmentEditor key={fragment.id} fragment={fragment} onSaved={saved} />)}
      </div>
      <div ref={sentinelRef} className="loading-sentinel">
        {loading ? <><i className="pi pi-spin pi-spinner" /> Загружаем следующие фрагменты…</> : hasMoreRef.current ? 'Прокрутите ниже для продолжения' : 'Все подходящие фрагменты загружены'}
      </div>
    </section>
  )
}
