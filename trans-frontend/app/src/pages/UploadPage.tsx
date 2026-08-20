import { useMemo, useState } from 'react'
import { useNavigate } from 'react-router'
import { Button } from 'primereact/button'
import { Column } from 'primereact/column'
import { DataTable } from 'primereact/datatable'
import { Dropdown } from 'primereact/dropdown'
import { FileUpload, type FileUploadSelectEvent } from 'primereact/fileupload'
import { InputText } from 'primereact/inputtext'
import { ProgressBar } from 'primereact/progressbar'
import { Tag } from 'primereact/tag'
import { useToastMessage } from '../app/ToastProvider'
import type { UploadBookInput } from '../domain/types'
import { bookService } from '../services/bookService'

interface UploadRow extends UploadBookInput {
  key: string
  progress: number
  status: 'ready' | 'uploading' | 'done' | 'error'
}

const languages = ['EN', 'DE', 'RU'].map((code) => ({ label: code, value: code }))

export function UploadPage() {
  const navigate = useNavigate()
  const toast = useToastMessage()
  const [rows, setRows] = useState<UploadRow[]>([])
  const [uploading, setUploading] = useState(false)

  const totalProgress = useMemo(() => rows.length
    ? Math.round(rows.reduce((sum, row) => sum + row.progress, 0) / rows.length)
    : 0, [rows])

  const selectFiles = (event: FileUploadSelectEvent) => {
    const selected = Array.from(event.files)
    setRows((current) => {
      const existing = new Set(current.map((row) => row.key))
      const additions = selected
        .map((file) => ({
          key: `${file.name}:${file.size}:${file.lastModified}`,
          file,
          title: file.name.replace(/\.pdf$/i, ''),
          sourceLanguage: 'EN',
          targetLanguage: 'RU',
          progress: 0,
          status: 'ready' as const,
        }))
        .filter((row) => !existing.has(row.key))
      return [...current, ...additions]
    })
  }

  const updateRow = (key: string, patch: Partial<UploadRow>) => {
    setRows((current) => current.map((row) => row.key === key ? { ...row, ...patch } : row))
  }

  const uploadAll = async () => {
    if (!rows.length || uploading) return
    setUploading(true)
    setRows((current) => current.map((row) => ({ ...row, status: 'uploading', progress: 0 })))
    try {
      await bookService.uploadBooks(rows, (index, progress) => {
        setRows((current) => current.map((row, rowIndex) => rowIndex === index
          ? { ...row, progress, status: progress === 100 ? 'done' : 'uploading' }
          : row))
      })
      toast.success(`${rows.length} файла загружены`, 'Все документы появились в общем списке.')
      navigate('/books')
    } catch (reason) {
      setRows((current) => current.map((row) => row.status === 'done' ? row : { ...row, status: 'error' }))
      toast.error('Загрузка не завершена', reason instanceof Error ? reason.message : 'Повторите попытку')
      setUploading(false)
    }
  }

  const statusBody = (row: UploadRow) => {
    if (row.status === 'uploading') return <div className="upload-progress"><Tag severity="info" value={`ЗАГРУЗКА · ${row.progress}%`} /><ProgressBar value={row.progress} showValue={false} /></div>
    if (row.status === 'done') return <Tag severity="success" value="ЗАГРУЖЕН" />
    if (row.status === 'error') return <Tag severity="danger" value="ОШИБКА" />
    return <Tag severity="success" value="PDF · ГОТОВ" />
  }

  return (
    <section>
      <div className="page-heading">
        <div><h1>Загрузка документов</h1><p>Выберите один или несколько PDF, проверьте название и языки.</p></div>
        <Button label="Отмена" outlined onClick={() => navigate('/books')} />
      </div>

      <div className="upload-dropzone">
        <i className="pi pi-cloud-upload" aria-hidden="true" />
        <div><strong>Выберите PDF-файлы</strong><small>Все выбранные файлы будут загружены одной пачкой</small></div>
        <FileUpload mode="basic" name="books" accept="application/pdf,.pdf" multiple chooseLabel="Выбрать файлы" disabled={uploading} onSelect={selectFiles} />
      </div>

      <div className="content-panel upload-table">
        <div className="panel-toolbar"><strong>{rows.length} файлов</strong><span>Общий прогресс: {totalProgress}%</span></div>
        <DataTable value={rows} dataKey="key" emptyMessage="Файлы ещё не выбраны" tableStyle={{ minWidth: '900px' }}>
          <Column header="Файл" body={(row: UploadRow) => <div><strong className="table-title">{row.file.name}</strong><small className="table-subtitle">{(row.file.size / 1024 / 1024).toFixed(1)} МБ</small></div>} />
          <Column header="Название" body={(row: UploadRow) => <InputText value={row.title} disabled={uploading} onChange={(event) => updateRow(row.key, { title: event.target.value })} />} />
          <Column header="Язык книги" body={(row: UploadRow) => <Dropdown value={row.sourceLanguage} options={languages} disabled={uploading} onChange={(event) => updateRow(row.key, { sourceLanguage: event.value as string })} />} />
          <Column header="Переводить на" body={(row: UploadRow) => <Dropdown value={row.targetLanguage} options={languages} disabled={uploading} onChange={(event) => updateRow(row.key, { targetLanguage: event.value as string })} />} />
          <Column header="Состояние" body={statusBody} />
          <Column header="" body={(row: UploadRow) => <Button icon="pi pi-trash" text severity="danger" aria-label={`Удалить ${row.file.name}`} disabled={uploading} onClick={() => setRows((current) => current.filter((item) => item.key !== row.key))} />} />
        </DataTable>
      </div>

      <div className="page-actions">
        <Button label="Назад" outlined disabled={uploading} onClick={() => navigate('/books')} />
        <Button label={uploading ? `Загрузка · ${totalProgress}%` : `Загрузить ${rows.length || ''} файла`} icon={uploading ? 'pi pi-spin pi-spinner' : 'pi pi-upload'} disabled={!rows.length || uploading} onClick={() => void uploadAll()} />
      </div>
    </section>
  )
}
