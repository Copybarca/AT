package io.copybarca.transapi.service;

import static org.junit.jupiter.api.Assertions.assertEquals;
import static org.mockito.Mockito.when;

import io.copybarca.transapi.model.Book;
import io.copybarca.transapi.model.PdfExtractionProcess;
import io.copybarca.transapi.model.ProcessStatus;
import io.copybarca.transapi.model.TranslationProcess;
import io.copybarca.transapi.repo.BookRepository;
import io.copybarca.transapi.repo.PdfBuildProcessRepository;
import io.copybarca.transapi.repo.PdfExtractionProcessRepository;
import io.copybarca.transapi.repo.SegmentRepository;
import io.copybarca.transapi.repo.TranslationProcessRepository;
import io.copybarca.transapi.repo.TranslationProgress;
import java.util.List;
import java.util.Optional;
import org.junit.jupiter.api.BeforeEach;
import org.junit.jupiter.api.Test;
import org.junit.jupiter.api.extension.ExtendWith;
import org.mockito.Mock;
import org.mockito.junit.jupiter.MockitoExtension;

@ExtendWith(MockitoExtension.class)
class BookQueryServiceTest {

    @Mock BookRepository books;
    @Mock PdfExtractionProcessRepository extractions;
    @Mock TranslationProcessRepository translations;
    @Mock PdfBuildProcessRepository builds;
    @Mock SegmentRepository segments;
    @Mock TranslationProgress progress;

    private BookQueryService service;

    @BeforeEach
    void setUp() {
        service = new BookQueryService(books, extractions, translations, builds, segments);
    }

    @Test
    void projectsRealPipelineStateForFrontend() {
        Book book = new Book("Manual", "eng");
        book.setId(7L);
        book.setPath("s3://bucket/books/7/original/manual.pdf");
        book.setOriginalFilename("manual.pdf");
        book.selectTargetLanguage("rus");
        PdfExtractionProcess extraction = new PdfExtractionProcess(book);
        extraction.complete();
        TranslationProcess translation = new TranslationProcess(book, "rus");

        when(books.findAll()).thenReturn(List.of(book));
        when(extractions.findByBook_Id(7L)).thenReturn(Optional.of(extraction));
        when(translations.findByBook_IdAndTargetLanguage(7L, "rus"))
                .thenReturn(Optional.of(translation));
        when(builds.findByBook_IdAndTargetLanguage(7L, "rus"))
                .thenReturn(Optional.empty());
        when(segments.translationProgress(7L, "rus")).thenReturn(progress);
        when(progress.getTotalFragments()).thenReturn(12L);
        when(progress.getTranslatedFragments()).thenReturn(3L);
        when(segments.countImagePositions(7L)).thenReturn(2L);

        var result = service.list("", "all");
        var item = result.items().getFirst();

        assertEquals(1, result.counters().all());
        assertEquals(1, result.counters().progress());
        assertEquals("complete", item.contentStatus());
        assertEquals("in_progress", item.translationStatus());
        assertEquals("missing", item.pdfStatus());
        assertEquals("manual.pdf", item.fileName());
        assertEquals("rus", item.targetLanguage());
        assertEquals(12, item.totalFragments());
        assertEquals(3, item.translatedFragments());
        assertEquals(2, item.imageCount());
    }

    @Test
    void statusFilterKeepsCountersForWholeCollection() {
        Book done = new Book("Done", "eng");
        done.setId(1L);
        done.setTranslatedPath("s3://bucket/result.pdf");
        done.selectTargetLanguage("rus");
        Book pending = new Book("Pending", "eng");
        pending.setId(2L);

        when(books.findAll()).thenReturn(List.of(done, pending));
        when(extractions.findByBook_Id(1L)).thenReturn(Optional.empty());
        when(extractions.findByBook_Id(2L)).thenReturn(Optional.empty());
        when(translations.findByBook_IdAndTargetLanguage(1L, "rus"))
                .thenReturn(Optional.empty());
        when(builds.findByBook_IdAndTargetLanguage(1L, "rus"))
                .thenReturn(Optional.empty());
        when(segments.translationProgress(1L, "rus")).thenReturn(progress);
        when(segments.countImagePositions(1L)).thenReturn(0L);
        when(segments.countImagePositions(2L)).thenReturn(0L);

        var result = service.list("", "done");

        assertEquals(2, result.counters().all());
        assertEquals(1, result.counters().done());
        assertEquals(List.of(1L), result.items().stream().map(item -> item.id()).toList());
    }
}
