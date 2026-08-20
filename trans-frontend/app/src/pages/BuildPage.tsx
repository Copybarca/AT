import { useEffect, useMemo, useState } from 'react'
import { useLocation } from 'react-router'
import { Button } from 'primereact/button'
import { Dialog } from 'primereact/dialog'
import { Dropdown } from 'primereact/dropdown'
import { Message } from 'primereact/message'
import { ProgressBar } from 'primereact/progressbar'
import { Tag } from 'primereact/tag'
import { useToastMessage } from '../app/ToastProvider'
import type { Book } from '../domain/types'
import { bookService } from '../services/bookService'

interface BuildLocationState { bookId?: number }

export function BuildPage() {
  const location = useLocation()
  const toast = useToastMessage()
  const [books, setBooks] = useState<Book[]>([])
  const [selectedId, setSelectedId] = useState<number | null>((location.state as BuildLocationState | null)?.bookId ?? null)
  const [confirmVisible, setConfirmVisible] = useState(false)
  const [progress, setProgress] = useState<number | null>(null)
  const [error, setError] = useState<string | null>(null)
  const selected = useMemo(() => books.find((book) => book.id === selectedId) ?? null, [books, selectedId])

  useEffect(() => {
    void bookService.listContentCompleteBooks().then(setBooks).catch((reason: unknown) => {
      setError(reason instanceof Error ? reason.message : 'Не удалось получить книги для сборки')
    })
  }, [])

  const updateSelected = (book: Book) => {
    setBooks((current) => current.map((item) => item.id === book.id ? book : item))
  }

  const runBuild = async (replaceExisting: boolean) => {
    if (!selected) return
    setConfirmVisible(false)
    setProgress(0)
    setError(null)
    try {
      const book = await bookService.buildDocument({
        bookId: selected.id,
        replaceExisting,
        onProgress: setProgress,
      })
      updateSelected(book)
      toast.success(
        replaceExisting ? 'Пересборка завершена' : 'Сборка завершена',
        replaceExisting ? 'Новый итоговый PDF заменил предыдущий результат.' : 'Итоговый PDF сохранён.',
      )
    } catch (reason) {
      const detail = reason instanceof Error ? reason.message : 'Повторите попытку'
      setError(detail)
      toast.error('Сборка не выполнена', detail)
    } finally {
      setProgress(null)
    }
  }

  const build = () => {
    if (!selected || selected.translationStatus === 'in_progress') return
    if (selected.pdfStatus === 'ready') setConfirmVisible(true)
    else void runBuild(false)
  }

  const translationState = selected?.translationStatus === 'completed'
    ? { label: 'БАЗА ПЕРЕВОДОВ ЗАПОЛНЕНА', severity: 'success' as const, detail: `${selected.translatedFragments} / ${selected.totalFragments} переводов сохранено` }
    : selected?.translationStatus === 'in_progress'
      ? { label: 'БАЗА ЗАПОЛНЯЕТСЯ', severity: 'info' as const, detail: `${selected.translatedFragments} / ${selected.totalFragments} переводов сохранено` }
      : { label: 'БАЗА ПЕРЕВОДОВ ПУСТА', severity: 'secondary' as const, detail: `0 / ${selected?.totalFragments ?? 0} переводов сохранено` }

  const blocked = selected?.translationStatus === 'in_progress'
  const rebuilding = selected?.pdfStatus === 'ready'

  return (
    <section>
      <div className="page-heading"><div><h1>Сборка итогового документа</h1><p>Выберите книгу с полностью загруженными текстами и изображениями.</p></div></div>
      {error && <Message severity="error" text={error} className="wide-message" />}
      <div className="selection-card build-selection">
        <label htmlFor="build-book">Книга, готовая к сборке</label>
        <Dropdown
          inputId="build-book"
          value={selectedId}
          options={books}
          optionValue="id"
          optionLabel="title"
          filter
          placeholder="Выберите книгу"
          disabled={progress != null}
          onChange={(event) => { setSelectedId(event.value as number); setError(null) }}
          itemTemplate={(book: Book) => <div><strong>{book.title}</strong><small className="table-subtitle">Книга #{book.id}</small></div>}
        />
        <Button
          label={blocked ? 'Сборка недоступна' : rebuilding ? 'Пересобрать документ' : 'Собрать документ'}
          icon={progress != null ? 'pi pi-spin pi-spinner' : 'pi pi-file-export'}
          disabled={!selected || blocked || progress != null}
          onClick={build}
        />
      </div>

      {selected && (
        <div className="build-state-grid">
          <article><small>Контент в базе</small><Tag severity="success" value="ЗАГРУЖЕН ПОЛНОСТЬЮ" /><p>{selected.totalFragments} текстов · {selected.imageCount} изображений</p></article>
          <article><small>База переводов</small><Tag severity={translationState.severity} value={translationState.label} /><p>{translationState.detail}</p></article>
          <article><small>Итоговый PDF</small><Tag severity={selected.pdfStatus === 'ready' ? 'success' : selected.pdfStatus === 'building' ? 'info' : 'secondary'} value={selected.pdfStatus === 'ready' ? 'PDF ГОТОВ' : selected.pdfStatus === 'building' ? 'PDF СОБИРАЕТСЯ' : 'PDF НЕ СОБРАН'} /><p>{selected.pdfStatus === 'ready' ? 'Файл уже сохранён' : 'Итогового файла пока нет'}</p></article>
          <article><small>Доступность действия</small><Tag severity={blocked ? 'danger' : rebuilding ? 'warning' : 'success'} value={blocked ? 'СБОРКА ЗАБЛОКИРОВАНА' : rebuilding ? 'ТРЕБУЕТСЯ ПОДТВЕРЖДЕНИЕ' : 'МОЖНО СОБИРАТЬ'} /><p>{blocked ? 'Дождитесь заполнения базы переводов' : rebuilding ? 'Готовый PDF будет заменён' : 'Первичная сборка доступна'}</p></article>
        </div>
      )}

      {blocked && <Message severity="warn" text="База переводов ещё заполняется. Сборка недоступна до завершения процесса." className="wide-message" />}
      {progress != null && <div className="build-progress-panel"><strong>{rebuilding ? 'Пересобираем и заменяем итоговый PDF…' : 'Собираем итоговый PDF…'}</strong><ProgressBar value={progress} /></div>}

      <Dialog
        header="Пересобрать готовый документ?"
        visible={confirmVisible}
        modal
        className="confirm-dialog"
        onHide={() => setConfirmVisible(false)}
        footer={(
          <div className="dialog-actions">
            <Button label="Нет, отменить" outlined onClick={() => { setConfirmVisible(false); toast.info('Пересборка отменена', 'Пересборка была отменена по вашему выбору.') }} />
            <Button label="Да, пересобрать" onClick={() => void runBuild(true)} />
          </div>
        )}
      >
        <p>Итоговый PDF уже существует. Новая сборка заменит сохранённый файл и связанные с ним данные.</p>
      </Dialog>
    </section>
  )
}
