package io.copybarca.transapi.service;

import static org.junit.jupiter.api.Assertions.assertEquals;
import static org.junit.jupiter.api.Assertions.assertFalse;
import static org.junit.jupiter.api.Assertions.assertTrue;
import static org.mockito.ArgumentMatchers.any;
import static org.mockito.Mockito.never;
import static org.mockito.Mockito.verify;
import static org.mockito.Mockito.when;

import io.copybarca.transapi.dto.client.TranslateTextRequest;
import io.copybarca.transapi.dto.client.TranslationDispatchAcceptedResponse;
import io.copybarca.transapi.dto.translation.TranslationFragmentResultRequest;
import io.copybarca.transapi.dto.translation.TranslationFragmentResultResponse;
import io.copybarca.transapi.dto.translation.TranslationResultStatus;
import io.copybarca.transapi.model.Book;
import io.copybarca.transapi.model.ProcessStatus;
import io.copybarca.transapi.model.Segment;
import io.copybarca.transapi.model.TextSegment;
import io.copybarca.transapi.model.TranslatedSegment;
import io.copybarca.transapi.model.TranslationProcess;
import io.copybarca.transapi.repo.SegmentRepository;
import io.copybarca.transapi.repo.TranslatablePosition;
import io.copybarca.transapi.repo.TranslatedSegmentRepository;
import io.copybarca.transapi.repo.TranslationProcessRepository;
import io.copybarca.transapi.restclient.AgentFlowClient;
import java.util.List;
import java.util.Optional;
import org.junit.jupiter.api.BeforeEach;
import org.junit.jupiter.api.Test;
import org.junit.jupiter.api.extension.ExtendWith;
import org.mockito.ArgumentCaptor;
import org.mockito.Mock;
import org.mockito.junit.jupiter.MockitoExtension;
import org.springframework.context.ApplicationEventPublisher;

@ExtendWith(MockitoExtension.class)
class TranslationPipelineServiceTest {

    @Mock
    private TranslationProcessRepository processes;

    @Mock
    private SegmentRepository segments;

    @Mock
    private TranslatedSegmentRepository translations;

    @Mock
    private AgentFlowClient agent;

    @Mock
    private TranslationResponseValidator validator;

    @Mock
    private ApplicationEventPublisher events;

    @Mock
    private TranslationProcess process;

    private TranslationPipelineService service;

    @BeforeEach
    void setUp() {
        service = new TranslationPipelineService(
                processes,
                segments,
                translations,
                agent,
                validator,
                events
        );
        when(processes.findById(11L)).thenReturn(Optional.of(process));
        org.mockito.Mockito.lenient().when(process.getId()).thenReturn(11L);
        when(process.getBookId()).thenReturn(42L);
        when(process.getTargetLanguage()).thenReturn("ru");
        when(process.getStatus()).thenReturn(ProcessStatus.IN_PROGRESS);
    }

    @Test
    void dispatchesExactlyOneSqlFragmentWithItsPrimaryKey() {
        TranslatablePosition position = org.mockito.Mockito.mock(TranslatablePosition.class);
        when(position.getSegmentId()).thenReturn(101L);
        when(position.getStableKey()).thenReturn("P0001-B001");
        when(position.getSourceHash()).thenReturn("sha256:source");
        when(position.getSourceLanguage()).thenReturn("en");
        when(position.getSourceText()).thenReturn("Hello 2.0");
        when(segments.findNextUntranslated(42L, "ru")).thenReturn(Optional.of(position));
        when(agent.submit(any())).thenReturn(
                new TranslationDispatchAcceptedResponse(
                        TranslationPipelineService.requestId(11L, 101L, "sha256:source"),
                        11L,
                        101L,
                        true
                )
        );

        service.run(11L);

        ArgumentCaptor<TranslateTextRequest> request =
                ArgumentCaptor.forClass(TranslateTextRequest.class);
        verify(agent).submit(request.capture());
        assertEquals(101L, request.getValue().segmentId());
        assertEquals("Hello 2.0", request.getValue().sourceText());
        assertEquals(
                "/internal/v1/books/42/translations/11/fragments/101",
                request.getValue().callbackPath()
        );
        verify(process, never()).complete();
    }

    @Test
    void validCallbackStoresOneTranslationAndSchedulesNextAfterCommit() {
        Segment segment = segment();
        when(segments.findById(101L)).thenReturn(Optional.of(segment));
        when(validator.validate(
                "P0001-B001",
                "Hello 2.0",
                "<<<P0001-B001>>>\nПривет 2.0"
        )).thenReturn(new TranslationValidationResult(true, "Привет 2.0", List.of()));

        TranslationFragmentResultResponse response = service.acceptFragment(
                42L,
                11L,
                101L,
                completedRequest()
        );

        assertTrue(response.accepted());
        assertEquals(ProcessStatus.IN_PROGRESS, response.processStatus());
        verify(translations).save(any(TranslatedSegment.class));
        verify(events).publishEvent(new TranslationFragmentStoredEvent(11L));
    }

    @Test
    void failedAgentCallbackMarksProcessFailedWithoutSavingText() {
        when(segments.findById(101L)).thenReturn(Optional.of(segment()));
        TranslationFragmentResultRequest request = new TranslationFragmentResultRequest(
                TranslationPipelineService.requestId(11L, 101L, "sha256:source"),
                "sha256:source",
                TranslationResultStatus.FAILED,
                null,
                "model",
                20L,
                "model unavailable"
        );

        TranslationFragmentResultResponse response = service.acceptFragment(
                42L,
                11L,
                101L,
                request
        );

        assertFalse(response.accepted());
        assertEquals(ProcessStatus.FAILED, response.processStatus());
        verify(process).fail();
        verify(translations, never()).save(any());
    }

    private static Segment segment() {
        Book book = new Book("Book", "en");
        book.setId(42L);
        Segment segment = new Segment(book, "P0001-B001", 1);
        segment.applyTextExtraction(
                new TextSegment("sha256:source", "Hello 2.0"),
                1,
                1,
                "{}",
                "BODY",
                true
        );
        return segment;
    }

    private static TranslationFragmentResultRequest completedRequest() {
        return new TranslationFragmentResultRequest(
                TranslationPipelineService.requestId(11L, 101L, "sha256:source"),
                "sha256:source",
                TranslationResultStatus.COMPLETED,
                "<<<P0001-B001>>>\nПривет 2.0",
                "model",
                20L,
                null
        );
    }
}
