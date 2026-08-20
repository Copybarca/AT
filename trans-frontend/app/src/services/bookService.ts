import type {
  Book,
  BookCounters,
  BookListResult,
  BookStatusFilter,
  BuildRequest,
  Fragment,
  FragmentPage,
  FragmentPageRequest,
  UploadBookInput,
} from '../domain/types'
import { createDemoFragments, demoBooks } from './demoData'

const API_BASE_URL = import.meta.env.VITE_API_BASE_URL?.replace(/\/$/, '') ?? ''
const demoBookState = structuredClone(demoBooks)
const demoFragments = new Map<number, Fragment[]>()

const wait = (milliseconds: number) => new Promise((resolve) => setTimeout(resolve, milliseconds))

function statusBucket(book: Book): Exclude<BookStatusFilter, 'all'> | 'other' {
  if (book.translationStatus === 'failed' || book.pdfStatus === 'failed' || book.contentStatus === 'failed') return 'failed'
  if (book.translationStatus === 'in_progress') return 'progress'
  if (book.pdfStatus === 'ready') return 'done'
  return 'other'
}

function countersFor(books: Book[]): BookCounters {
  return books.reduce<BookCounters>((counters, book) => {
    counters.all += 1
    const bucket = statusBucket(book)
    if (bucket !== 'other') counters[bucket] += 1
    return counters
  }, { all: 0, progress: 0, done: 0, failed: 0 })
}

async function request<T>(path: string, init?: RequestInit): Promise<T> {
  const response = await fetch(`${API_BASE_URL}${path}`, {
    credentials: 'include',
    ...init,
    headers: init?.body instanceof FormData
      ? init.headers
      : { 'Content-Type': 'application/json', ...init?.headers },
  })
  if (!response.ok) throw new Error(`HTTP ${response.status}: ${response.statusText}`)
  return response.json() as Promise<T>
}

function getDemoFragments(bookId: number): Fragment[] {
  if (!demoFragments.has(bookId)) demoFragments.set(bookId, createDemoFragments(bookId))
  return demoFragments.get(bookId) ?? []
}

export const bookService = {
  async listBooks(search = '', filter: BookStatusFilter = 'all'): Promise<BookListResult> {
    if (API_BASE_URL) {
      const params = new URLSearchParams({ search, status: filter })
      return request<BookListResult>(`/books?${params}`)
    }
    await wait(120)
    const normalizedSearch = search.trim().toLocaleLowerCase('ru')
    const items = demoBookState
      .filter((book) => !normalizedSearch || book.title.toLocaleLowerCase('ru').includes(normalizedSearch))
      .filter((book) => filter === 'all' || statusBucket(book) === filter)
      .sort((left, right) => right.id - left.id)
    return { items: structuredClone(items), counters: countersFor(demoBookState) }
  },

  async getBook(bookId: number): Promise<Book> {
    if (API_BASE_URL) return request<Book>(`/books/${bookId}`)
    await wait(80)
    const book = demoBookState.find((item) => item.id === bookId)
    if (!book) throw new Error(`Книга #${bookId} не найдена`)
    return structuredClone(book)
  },

  async uploadBooks(
    inputs: UploadBookInput[],
    onProgress?: (index: number, percent: number) => void,
  ): Promise<Book[]> {
    const uploadOne = async (input: UploadBookInput, index: number): Promise<Book> => {
      for (const percent of [15, 35, 60, 85]) {
        await wait(90)
        onProgress?.(index, percent)
      }
      if (API_BASE_URL) {
        const form = new FormData()
        form.append('file', input.file)
        form.append('title', input.title)
        form.append('sourceLanguage', input.sourceLanguage)
        form.append('targetLanguage', input.targetLanguage)
        const book = await request<Book>('/books', { method: 'POST', body: form })
        onProgress?.(index, 100)
        return book
      }
      const id = Math.max(...demoBookState.map((book) => book.id), 0) + 1
      const book: Book = {
        id,
        title: input.title || input.file.name.replace(/\.pdf$/i, ''),
        fileName: input.file.name,
        sourceLanguage: input.sourceLanguage,
        targetLanguage: input.targetLanguage,
        contentStatus: 'complete',
        translationStatus: 'not_started',
        pdfStatus: 'missing',
        totalFragments: 240 + index * 17,
        translatedFragments: 0,
        imageCount: 30 + index * 4,
        updatedAt: new Date().toISOString(),
      }
      demoBookState.push(book)
      onProgress?.(index, 100)
      return structuredClone(book)
    }
    return Promise.all(inputs.map(uploadOne))
  },

  async listContentCompleteBooks(): Promise<Book[]> {
    if (API_BASE_URL) return request<Book[]>('/books/buildable')
    await wait(100)
    return structuredClone(demoBookState.filter((book) => book.contentStatus === 'complete'))
  },

  async getFragments(pageRequest: FragmentPageRequest): Promise<FragmentPage> {
    const { bookId, afterSequence, limit, filter } = pageRequest
    if (API_BASE_URL) {
      const params = new URLSearchParams({
        limit: String(limit),
        filter,
        ...(afterSequence == null ? {} : { afterSequence: String(afterSequence) }),
      })
      return request<FragmentPage>(`/books/${bookId}/fragments?${params}`)
    }
    await wait(120)
    const eligible = getDemoFragments(bookId)
      .filter((fragment) => fragment.sequence > (afterSequence ?? 0))
      .filter((fragment) => filter === 'all' || !fragment.translatedText)
      .sort((left, right) => left.sequence - right.sequence)
    const items = eligible.slice(0, limit)
    return {
      items: structuredClone(items),
      nextSequence: eligible.length > items.length && items.length
        ? items[items.length - 1].sequence
        : null,
    }
  },

  async saveFragmentTranslation(bookId: number, fragmentId: number, translatedText: string): Promise<Fragment> {
    if (!translatedText.trim()) throw new Error('Перевод не может быть пустым')
    if (API_BASE_URL) {
      return request<Fragment>(`/books/${bookId}/fragments/${fragmentId}/translation`, {
        method: 'PUT',
        body: JSON.stringify({ translatedText }),
      })
    }
    await wait(180)
    const fragment = getDemoFragments(bookId).find((item) => item.id === fragmentId)
    if (!fragment) throw new Error('Фрагмент не найден')
    fragment.translatedText = translatedText.trim()
    fragment.version += 1
    return structuredClone(fragment)
  },

  async buildDocument(buildRequest: BuildRequest): Promise<Book> {
    const { bookId, replaceExisting, onProgress } = buildRequest
    if (API_BASE_URL) {
      return request<Book>(`/books/${bookId}/build`, {
        method: 'POST',
        body: JSON.stringify({ replaceExisting }),
      })
    }
    const book = demoBookState.find((item) => item.id === bookId)
    if (!book) throw new Error('Книга не найдена')
    if (book.contentStatus !== 'complete') throw new Error('Контент книги загружен не полностью')
    if (book.translationStatus === 'in_progress') throw new Error('Сборка недоступна во время перевода')
    if (book.pdfStatus === 'ready' && !replaceExisting) throw new Error('Для готового PDF требуется подтверждённая пересборка')
    book.pdfStatus = 'building'
    for (const percent of [15, 35, 55, 75, 100]) {
      await wait(100)
      onProgress?.(percent)
    }
    book.pdfStatus = 'ready'
    book.updatedAt = new Date().toISOString()
    return structuredClone(book)
  },
}

export function resetDemoStateForTests(): void {
  demoBookState.splice(0, demoBookState.length, ...structuredClone(demoBooks))
  demoFragments.clear()
}
