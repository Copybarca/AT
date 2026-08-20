import { afterEach, describe, expect, it, vi } from 'vitest'
import type { Book } from '../domain/types'
import { bookService } from './bookService'

const readyBook: Book = {
  id: 7,
  title: 'Two pages',
  fileName: 'two-pages.pdf',
  sourceLanguage: 'eng',
  targetLanguage: 'rus',
  contentStatus: 'uploading',
  translationStatus: 'in_progress',
  pdfStatus: 'missing',
  totalFragments: 0,
  translatedFragments: 0,
  imageCount: 0,
  updatedAt: '2026-08-20T12:00:00Z',
}

function json(value: unknown, status = 200): Response {
  return new Response(JSON.stringify(value), {
    status,
    headers: { 'Content-Type': 'application/json' },
  })
}

afterEach(() => vi.unstubAllGlobals())

describe('bookService real API adapter', () => {
  it('creates a book, starts translation, then returns factual backend DTO', async () => {
    const fetchMock = vi.fn()
      .mockResolvedValueOnce(json({ id: 7 }, 201))
      .mockResolvedValueOnce(json({ bookId: 7, targetLanguage: 'rus' }, 202))
      .mockResolvedValueOnce(json(readyBook))
    vi.stubGlobal('fetch', fetchMock)
    const progress = vi.fn()
    const file = new File(['%PDF-1.7'], 'two-pages.pdf', { type: 'application/pdf' })

    const result = await bookService.uploadBooks([{
      file,
      title: 'Two pages',
      sourceLanguage: 'eng',
      targetLanguage: 'rus',
    }], progress)

    expect(result).toEqual([readyBook])
    expect(fetchMock).toHaveBeenCalledTimes(3)
    expect(fetchMock.mock.calls[0][0]).toBe('/api/v1/books')
    const createForm = fetchMock.mock.calls[0][1]?.body as FormData
    expect(createForm.get('originalLanguage')).toBe('eng')
    expect(createForm.get('sourceLanguage')).toBeNull()
    expect(fetchMock.mock.calls[1][0]).toBe('/api/v1/books/7/translations')
    expect(fetchMock.mock.calls[1][1]?.body).toBe('{"targetLanguage":"rus"}')
    expect(progress).toHaveBeenLastCalledWith(0, 100)
  })

  it('sends explicit language for cursor paging and manual save', async () => {
    const fragment = {
      id: 9,
      bookId: 7,
      sequence: 4,
      originalText: 'Original',
      translatedText: null,
      version: 0,
    }
    const fetchMock = vi.fn()
      .mockResolvedValueOnce(json({ items: [fragment], nextSequence: null }))
      .mockResolvedValueOnce(json({ ...fragment, translatedText: 'Перевод', version: 1 }))
    vi.stubGlobal('fetch', fetchMock)

    await bookService.getFragments({
      bookId: 7,
      targetLanguage: 'rus',
      afterSequence: null,
      limit: 6,
      filter: 'untranslated',
    })
    await bookService.saveFragmentTranslation(7, 9, 'rus', 'Перевод')

    expect(fetchMock.mock.calls[0][0]).toContain('targetLanguage=rus')
    expect(fetchMock.mock.calls[1][1]?.body)
      .toBe('{"targetLanguage":"rus","translatedText":"Перевод"}')
  })

  it('sends confirmed rebuild and exposes a stable download URL', async () => {
    const fetchMock = vi.fn().mockResolvedValueOnce(json({ ...readyBook, pdfStatus: 'ready' }))
    vi.stubGlobal('fetch', fetchMock)

    await bookService.buildDocument({
      bookId: 7,
      targetLanguage: 'rus',
      replaceExisting: true,
    })

    expect(fetchMock.mock.calls[0][1]?.body)
      .toBe('{"targetLanguage":"rus","replaceExisting":true}')
    expect(bookService.translatedPdfUrl(7, 'rus'))
      .toBe('/api/v1/books/7/translated?targetLanguage=rus')
  })
})
