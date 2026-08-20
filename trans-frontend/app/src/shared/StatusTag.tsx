import { Tag, type TagProps } from 'primereact/tag'
import type { Book, PdfStatus, TranslationStatus } from '../domain/types'

const translationLabels: Record<TranslationStatus, string> = {
  not_started: 'НЕ ПЕРЕВОДИЛСЯ',
  in_progress: 'ПЕРЕВОДИТСЯ',
  completed: 'ПЕРЕВОД ГОТОВ',
  failed: 'ОШИБКА ПЕРЕВОДА',
}

const pdfLabels: Record<PdfStatus, string> = {
  missing: 'PDF НЕ СОБРАН',
  building: 'PDF СОБИРАЕТСЯ',
  ready: 'PDF ГОТОВ',
  failed: 'ОШИБКА PDF',
}

function translationSeverity(status: TranslationStatus): TagProps['severity'] {
  if (status === 'completed') return 'success'
  if (status === 'failed') return 'danger'
  if (status === 'in_progress') return 'info'
  return 'secondary'
}

function pdfSeverity(status: PdfStatus): TagProps['severity'] {
  if (status === 'ready') return 'success'
  if (status === 'failed') return 'danger'
  if (status === 'building') return 'info'
  return 'secondary'
}

export function TranslationStatusTag({ status }: { status: TranslationStatus }) {
  return <Tag severity={translationSeverity(status)} value={translationLabels[status]} />
}

export function PdfStatusTag({ status }: { status: PdfStatus }) {
  return <Tag severity={pdfSeverity(status)} value={pdfLabels[status]} />
}

export function BookMainStatusTag({ book }: { book: Book }) {
  if (book.contentStatus === 'uploading') return <Tag severity="info" value="ЗАГРУЗКА" />
  if (book.contentStatus === 'failed') return <Tag severity="danger" value="ОШИБКА ЗАГРУЗКИ" />
  if (book.pdfStatus === 'ready') return <Tag severity="success" value="ГОТОВ" />
  return <TranslationStatusTag status={book.translationStatus} />
}
