import type { Book, Fragment } from '../domain/types'

export const demoBooks: Book[] = [
  {
    id: 42,
    title: 'Designing Data-Intensive Applications',
    fileName: 'designing-data-intensive-applications.pdf',
    sourceLanguage: 'EN',
    targetLanguage: 'RU',
    contentStatus: 'complete',
    translationStatus: 'not_started',
    pdfStatus: 'missing',
    totalFragments: 1358,
    translatedFragments: 0,
    imageCount: 612,
    updatedAt: '2026-08-20T08:43:08Z',
  },
  {
    id: 39,
    title: 'OAuth 2 in Action',
    fileName: 'oauth-2-in-action.pdf',
    sourceLanguage: 'EN',
    targetLanguage: 'RU',
    contentStatus: 'complete',
    translationStatus: 'in_progress',
    pdfStatus: 'missing',
    totalFragments: 982,
    translatedFragments: 668,
    imageCount: 284,
    updatedAt: '2026-08-20T08:41:22Z',
  },
  {
    id: 35,
    title: 'PostgreSQL Internals',
    fileName: 'postgresql-internals.pdf',
    sourceLanguage: 'EN',
    targetLanguage: 'RU',
    contentStatus: 'complete',
    translationStatus: 'completed',
    pdfStatus: 'ready',
    totalFragments: 1146,
    translatedFragments: 1146,
    imageCount: 436,
    updatedAt: '2026-08-20T07:13:04Z',
  },
  {
    id: 31,
    title: 'Distributed Systems',
    fileName: 'distributed-systems.pdf',
    sourceLanguage: 'EN',
    targetLanguage: 'RU',
    contentStatus: 'complete',
    translationStatus: 'completed',
    pdfStatus: 'missing',
    totalFragments: 876,
    translatedFragments: 876,
    imageCount: 198,
    updatedAt: '2026-08-19T18:12:54Z',
  },
  {
    id: 44,
    title: 'Новый документ',
    fileName: 'new-document.pdf',
    sourceLanguage: 'EN',
    targetLanguage: 'RU',
    contentStatus: 'uploading',
    translationStatus: 'not_started',
    pdfStatus: 'missing',
    totalFragments: 0,
    translatedFragments: 0,
    imageCount: 0,
    updatedAt: '2026-08-20T09:01:15Z',
  },
]

const originals = [
  'A distributed system is one in which the failure of a computer you did not even know existed can render your own computer unusable.',
  'Reliability means continuing to work correctly, even when things go wrong.',
  'The systems we build need to be reliable, scalable, and maintainable.',
  'A fault is usually defined as one component of the system deviating from its specification.',
  'It is impossible to reduce the probability of a fault to zero.',
  'Scalability describes a system’s ability to cope with increased load.',
]

const translations = [
  'Распределённая система — это система, в которой отказ неизвестного вам компьютера может сделать ваш компьютер непригодным для работы.',
  null,
  'Создаваемые нами системы должны быть надёжными, масштабируемыми и удобными в сопровождении.',
  null,
  null,
  'Масштабируемость описывает способность системы справляться с возрастающей нагрузкой.',
]

export function createDemoFragments(bookId: number): Fragment[] {
  return Array.from({ length: 36 }, (_, index) => {
    const sequence = index + 1
    const templateIndex = index % originals.length
    return {
      id: bookId * 1000 + sequence,
      bookId,
      sequence,
      originalText: `${originals[templateIndex]} (${sequence})`,
      translatedText: bookId === 42 ? translations[templateIndex] : null,
      version: 1,
    }
  })
}
