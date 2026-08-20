package io.copybarca.transapi.service;

import static org.junit.jupiter.api.Assertions.assertEquals;
import static org.junit.jupiter.api.Assertions.assertNull;
import static org.mockito.ArgumentMatchers.any;
import static org.mockito.Mockito.verify;
import static org.mockito.Mockito.when;

import io.copybarca.transapi.model.Book;
import io.copybarca.transapi.model.PdfBuildProcess;
import io.copybarca.transapi.model.Segment;
import io.copybarca.transapi.model.TextSegment;
import io.copybarca.transapi.model.TranslatedSegment;
import io.copybarca.transapi.model.TranslatedSegmentId;
import io.copybarca.transapi.repo.BookRepository;
import io.copybarca.transapi.repo.PdfBuildProcessRepository;
import io.copybarca.transapi.repo.SegmentRepository;
import io.copybarca.transapi.repo.TranslatedSegmentRepository;
import java.util.List;
import java.util.Optional;
import org.junit.jupiter.api.BeforeEach;
import org.junit.jupiter.api.Test;
import org.junit.jupiter.api.extension.ExtendWith;
import org.mockito.Mock;
import org.mockito.junit.jupiter.MockitoExtension;
import org.springframework.test.util.ReflectionTestUtils;

@ExtendWith(MockitoExtension.class)
class FragmentServiceTest {

    @Mock BookRepository books;
    @Mock SegmentRepository segments;
    @Mock TranslatedSegmentRepository translated;
    @Mock PdfBuildProcessRepository builds;

    private FragmentService service;
    private Book book;
    private Segment segment;
    private TextSegment text;

    @BeforeEach
    void setUp() {
        service = new FragmentService(books, segments, translated, builds);
        book = new Book("Manual", "eng");
        book.setId(7L);
        book.selectTargetLanguage("rus");
        text = new TextSegment("sha256:text", "Original text.");
        segment = new Segment(book, "P0001-B001", 4);
        segment.setTextSegment(text);
        ReflectionTestUtils.setField(segment, "id", 9L);
    }

    @Test
    void pagesFragmentsInSequenceAndIncludesExistingTranslation() {
        when(books.existsById(7L)).thenReturn(true);
        when(segments.findByBook_IdOrderBySequentialNumber(7L))
                .thenReturn(List.of(segment));
        when(translated.findById(new TranslatedSegmentId("sha256:text", "rus")))
                .thenReturn(Optional.of(new TranslatedSegment(text, "rus", "Перевод.")));

        var page = service.page(7L, "rus", "all", 0, 10);

        assertEquals(1, page.items().size());
        assertEquals(4, page.items().getFirst().sequence());
        assertEquals("Original text.", page.items().getFirst().originalText());
        assertEquals("Перевод.", page.items().getFirst().translatedText());
        assertNull(page.nextSequence());
    }

    @Test
    void manualSaveInvalidatesCompletedPdf() {
        book.setTranslatedPath("s3://bucket/translated.pdf");
        PdfBuildProcess build = new PdfBuildProcess(book, "rus");
        build.complete();
        when(segments.findById(9L)).thenReturn(Optional.of(segment));
        when(translated.findById(new TranslatedSegmentId("sha256:text", "rus")))
                .thenReturn(Optional.empty());
        when(builds.findByBook_IdAndTargetLanguage(7L, "rus"))
                .thenReturn(Optional.of(build));

        var response = service.save(7L, 9L, "rus", " Новый перевод ");

        assertEquals("Новый перевод", response.translatedText());
        verify(translated).save(any(TranslatedSegment.class));
        verify(builds).delete(build);
        assertNull(book.getTranslatedPath());
    }
}
