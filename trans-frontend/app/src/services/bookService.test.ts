import { beforeEach, describe, expect, it, vi } from 'vitest'
import { bookService, resetDemoStateForTests } from './bookService'

describe('bookService demo adapter', () => {
  beforeEach(() => resetDemoStateForTests())

  it('filters books and returns global counters', async () => {
    const result = await bookService.listBooks('', 'progress')
    expect(result.items.map((book) => book.id)).toEqual([39])
    expect(result.counters).toEqual({ all: 5, progress: 1, done: 1, failed: 0 })
  })

  it('uploads the whole selected batch and reports completion', async () => {
    const progress = vi.fn()
    const books = await bookService.uploadBooks([
      { file: new File(['one'], 'one.pdf', { type: 'application/pdf' }), title: 'One', sourceLanguage: 'EN', targetLanguage: 'RU' },
      { file: new File(['two'], 'two.pdf', { type: 'application/pdf' }), title: 'Two', sourceLanguage: 'DE', targetLanguage: 'RU' },
    ], progress)

    expect(books).toHaveLength(2)
    expect(progress).toHaveBeenCalledWith(0, 100)
    expect(progress).toHaveBeenCalledWith(1, 100)
    const list = await bookService.listBooks('', 'all')
    expect(list.counters.all).toBe(7)
  })

  it('pages fragments by ascending sequence and saves one translation', async () => {
    const first = await bookService.getFragments({ bookId: 42, afterSequence: null, limit: 3, filter: 'all' })
    expect(first.items.map((fragment) => fragment.sequence)).toEqual([1, 2, 3])
    expect(first.nextSequence).toBe(3)

    const second = await bookService.getFragments({ bookId: 42, afterSequence: first.nextSequence, limit: 3, filter: 'untranslated' })
    expect(second.items.map((fragment) => fragment.sequence)).toEqual([4, 5, 8])

    const saved = await bookService.saveFragmentTranslation(42, second.items[0].id, 'Ручной перевод')
    expect(saved.translatedText).toBe('Ручной перевод')
    expect(saved.version).toBe(2)
  })

  it('enforces build and rebuild rules', async () => {
    await expect(bookService.buildDocument({ bookId: 39, replaceExisting: false })).rejects.toThrow('во время перевода')
    await expect(bookService.buildDocument({ bookId: 35, replaceExisting: false })).rejects.toThrow('подтверждённая пересборка')

    const built = await bookService.buildDocument({ bookId: 31, replaceExisting: false })
    expect(built.pdfStatus).toBe('ready')
    const rebuilt = await bookService.buildDocument({ bookId: 35, replaceExisting: true })
    expect(rebuilt.pdfStatus).toBe('ready')
  })
})
