package io.copybarca.transapi.service;

import static org.junit.jupiter.api.Assertions.assertEquals;
import static org.mockito.ArgumentMatchers.any;
import static org.mockito.Mockito.when;

import io.copybarca.transapi.model.Book;
import io.copybarca.transapi.model.PdfExtractionProcess;
import io.copybarca.transapi.repo.BookRepository;
import io.copybarca.transapi.repo.PdfBuildProcessRepository;
import io.copybarca.transapi.repo.PdfExtractionProcessRepository;
import io.copybarca.transapi.repo.SegmentRepository;
import io.copybarca.transapi.repo.TranslationProcessRepository;
import java.util.Optional;
import org.junit.jupiter.api.Test;
import org.junit.jupiter.api.extension.ExtendWith;
import org.mockito.Mock;
import org.mockito.junit.jupiter.MockitoExtension;

@ExtendWith(MockitoExtension.class)
class PipelineProcessServiceTest {

    @Mock BookRepository books;
    @Mock PdfExtractionProcessRepository extractions;
    @Mock TranslationProcessRepository translations;
    @Mock PdfBuildProcessRepository builds;
    @Mock SegmentRepository segments;
    @Mock PipelineTaskQueue queue;
    @Mock PdfExtractionDispatchService extractionDispatcher;
    @Mock TranslationPipelineService translationPipeline;
    @Mock PdfBuildDispatchService buildDispatcher;
    @Mock PipelineFailureService failures;

    @Test
    void remembersSelectedTargetLanguageWhenPipelineStarts() {
        Book book = new Book("Manual", "eng");
        book.setId(7L);
        book.setPath("s3://bucket/manual.pdf");
        when(books.findById(7L)).thenReturn(Optional.of(book));
        when(extractions.findByBook_Id(7L)).thenReturn(Optional.empty());
        when(extractions.save(any())).thenAnswer(invocation -> invocation.getArgument(0));
        when(translations.findByBook_IdAndTargetLanguage(7L, "rus"))
                .thenReturn(Optional.empty());
        when(translations.save(any())).thenAnswer(invocation -> invocation.getArgument(0));

        var service = new PipelineProcessService(
                books, extractions, translations, builds, segments, queue,
                extractionDispatcher, translationPipeline, buildDispatcher, failures
        );

        service.start(7L, " rus ");

        assertEquals("rus", book.getTargetLanguage());
    }
}
