export type TranslationStatus = 'not_started' | 'in_progress' | 'completed' | 'failed'
export type PdfStatus = 'missing' | 'building' | 'ready' | 'failed'
export type ContentStatus = 'uploading' | 'complete' | 'failed'
export type BookStatusFilter = 'all' | 'progress' | 'done' | 'failed'
export type FragmentFilter = 'all' | 'untranslated'

export interface Book {
  id: number
  title: string
  fileName: string
  sourceLanguage: string
  targetLanguage: string
  contentStatus: ContentStatus
  translationStatus: TranslationStatus
  pdfStatus: PdfStatus
  totalFragments: number
  translatedFragments: number
  imageCount: number
  updatedAt: string
}

export interface BookCounters {
  all: number
  progress: number
  done: number
  failed: number
}

export interface BookListResult {
  items: Book[]
  counters: BookCounters
}

export interface UploadBookInput {
  file: File
  title: string
  sourceLanguage: string
  targetLanguage: string
}

export interface Fragment {
  id: number
  bookId: number
  sequence: number
  originalText: string
  translatedText: string | null
  version: number
}

export interface FragmentPage {
  items: Fragment[]
  nextSequence: number | null
}

export interface FragmentPageRequest {
  bookId: number
  afterSequence: number | null
  limit: number
  filter: FragmentFilter
}

export interface BuildRequest {
  bookId: number
  replaceExisting: boolean
  onProgress?: (percent: number) => void
}
