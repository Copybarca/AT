package io.copybarca.transapi.service;

import static org.junit.jupiter.api.Assertions.assertThrows;
import static org.mockito.ArgumentMatchers.any;
import static org.mockito.ArgumentMatchers.anyString;
import static org.mockito.Mockito.when;

import io.copybarca.transapi.model.Book;
import io.copybarca.transapi.model.PdfExtractionProcess;
import io.copybarca.transapi.model.TranslationProcess;
import io.copybarca.transapi.repo.BookRepository;
import io.copybarca.transapi.repo.PdfBuildProcessRepository;
import io.copybarca.transapi.repo.PdfExtractionProcessRepository;
import io.copybarca.transapi.repo.TranslationProcessRepository;
import java.util.Optional;
import org.junit.jupiter.api.Test;
import org.junit.jupiter.api.extension.ExtendWith;
import org.mockito.Mock;
import org.mockito.junit.jupiter.MockitoExtension;

@ExtendWith(MockitoExtension.class)
class PublicBuildServiceTest {

    @Mock BookRepository books;
    @Mock PdfExtractionProcessRepository extractions;
    @Mock TranslationProcessRepository translations;
    @Mock PdfBuildProcessRepository builds;
    @Mock PipelineTaskQueue queue;
    @Mock PdfBuildDispatchService dispatcher;
    @Mock PipelineFailureService failures;

    @Test
    void rejectsBuildUntilTranslationCompletes() {
        Book book = new Book("Manual", "eng");
        book.setId(7L);
        PdfExtractionProcess extraction = new PdfExtractionProcess(book);
        extraction.complete();
        TranslationProcess translation = new TranslationProcess(book, "rus");

        when(books.findById(7L)).thenReturn(Optional.of(book));
        when(extractions.findByBook_Id(7L)).thenReturn(Optional.of(extraction));
        when(translations.findByBook_IdAndTargetLanguage(7L, "rus"))
                .thenReturn(Optional.of(translation));

        var service = new PublicBuildService(
                books, extractions, translations, builds, queue, dispatcher, failures
        );

        assertThrows(
                IllegalStateException.class,
                () -> service.start(7L, "rus", false)
        );
    }
}
