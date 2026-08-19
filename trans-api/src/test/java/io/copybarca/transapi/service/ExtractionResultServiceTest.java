package io.copybarca.transapi.service;

import static org.junit.jupiter.api.Assertions.assertThrows;
import static org.mockito.Mockito.verify;
import static org.mockito.Mockito.when;

import io.copybarca.transapi.dto.extraction.ExtractionCompleteRequest;
import io.copybarca.transapi.model.PdfExtractionProcess;
import io.copybarca.transapi.repo.BookRepository;
import io.copybarca.transapi.repo.InsertionRepository;
import io.copybarca.transapi.repo.InsertionTextRegionRepository;
import io.copybarca.transapi.repo.PdfExtractionProcessRepository;
import io.copybarca.transapi.repo.SegmentRepository;
import io.copybarca.transapi.repo.TextSegmentRepository;
import java.util.Optional;
import org.junit.jupiter.api.BeforeEach;
import org.junit.jupiter.api.Test;
import org.junit.jupiter.api.extension.ExtendWith;
import org.mockito.Mock;
import org.mockito.junit.jupiter.MockitoExtension;

@ExtendWith(MockitoExtension.class)
class ExtractionResultServiceTest {

    @Mock
    private BookRepository books;

    @Mock
    private PdfExtractionProcessRepository processes;

    @Mock
    private TextSegmentRepository texts;

    @Mock
    private SegmentRepository segments;

    @Mock
    private InsertionRepository insertions;

    @Mock
    private InsertionTextRegionRepository regions;

    @Mock
    private BookFileStorage storage;

    @Mock
    private PdfExtractionProcess process;

    private ExtractionResultService service;

    @BeforeEach
    void setUp() {
        service = new ExtractionResultService(
                books,
                processes,
                texts,
                segments,
                insertions,
                regions,
                storage
        );
        when(processes.findById(91L)).thenReturn(Optional.of(process));
        when(process.getBookId()).thenReturn(42L);
    }

    @Test
    void rejectsCompletionWhenStoredCountsDoNotMatchManifest() {
        when(segments.countTextPositions(42L)).thenReturn(9L);
        when(segments.countImagePositions(42L)).thenReturn(2L);
        when(regions.countByBookId(42L)).thenReturn(3L);

        assertThrows(
                ExtractionCountMismatchException.class,
                () -> service.complete(
                        42L,
                        new ExtractionCompleteRequest(
                                91L,
                                "sha256:pdf",
                                "extractor-v1",
                                10,
                                2,
                                3
                        )
                )
        );
    }

    @Test
    void recordsManifestAndCompletesOnlyWhenAllCountsMatch() {
        when(segments.countTextPositions(42L)).thenReturn(10L);
        when(segments.countImagePositions(42L)).thenReturn(2L);
        when(regions.countByBookId(42L)).thenReturn(3L);

        service.complete(
                42L,
                new ExtractionCompleteRequest(
                        91L,
                        "sha256:pdf",
                        "extractor-v1",
                        10,
                        2,
                        3
                )
        );

        verify(process).recordManifest(
                "sha256:pdf",
                "extractor-v1",
                10,
                2,
                3
        );
        verify(process).complete();
    }
}
