package io.copybarca.transapi.service;

import io.copybarca.transapi.dto.client.TranslateTextRequest;
import io.copybarca.transapi.dto.translation.TranslationFragmentResultRequest;
import io.copybarca.transapi.dto.translation.TranslationFragmentResultResponse;
import io.copybarca.transapi.dto.translation.TranslationResultStatus;
import io.copybarca.transapi.model.ProcessStatus;
import io.copybarca.transapi.model.Segment;
import io.copybarca.transapi.model.TextSegment;
import io.copybarca.transapi.model.TranslatedSegment;
import io.copybarca.transapi.model.TranslatedSegmentId;
import io.copybarca.transapi.model.TranslationProcess;
import io.copybarca.transapi.repo.SegmentRepository;
import io.copybarca.transapi.repo.TranslatablePosition;
import io.copybarca.transapi.repo.TranslatedSegmentRepository;
import io.copybarca.transapi.repo.TranslationProcessRepository;
import io.copybarca.transapi.restclient.AgentFlowClient;
import java.nio.charset.StandardCharsets;
import java.util.List;
import java.util.UUID;
import org.springframework.context.ApplicationEventPublisher;
import org.springframework.stereotype.Service;
import org.springframework.transaction.annotation.Transactional;
import org.springframework.util.StringUtils;

@Service
public class TranslationPipelineService {

    private final TranslationProcessRepository processes;
    private final SegmentRepository segments;
    private final TranslatedSegmentRepository translations;
    private final AgentFlowClient agent;
    private final TranslationResponseValidator validator;
    private final ApplicationEventPublisher events;

    public TranslationPipelineService(
            TranslationProcessRepository processes,
            SegmentRepository segments,
            TranslatedSegmentRepository translations,
            AgentFlowClient agent,
            TranslationResponseValidator validator,
            ApplicationEventPublisher events
    ) {
        this.processes = processes;
        this.segments = segments;
        this.translations = translations;
        this.agent = agent;
        this.validator = validator;
        this.events = events;
    }

    /**
     * Selects and dispatches at most one untranslated SQL segment. The agent
     * callback commits that segment before the next invocation is scheduled.
     */
    @Transactional
    public void run(Long processId) {
        TranslationProcess process = requireProcess(processId);
        if (process.getStatus() != ProcessStatus.IN_PROGRESS) {
            return;
        }

        TranslatablePosition position = segments.findNextUntranslated(
                        process.getBookId(),
                        process.getTargetLanguage()
                )
                .orElse(null);
        if (position == null) {
            process.complete();
            events.publishEvent(
                    new TranslationCompletedEvent(
                            process.getId(),
                            process.getBookId(),
                            process.getTargetLanguage()
                    )
            );
            return;
        }

        String requestId = requestId(processId, position.getSegmentId(), position.getSourceHash());
        agent.submit(
                new TranslateTextRequest(
                        process.getId(),
                        process.getBookId(),
                        position.getSegmentId(),
                        requestId,
                        position.getStableKey(),
                        position.getSourceHash(),
                        position.getSourceLanguage(),
                        process.getTargetLanguage(),
                        position.getSourceText(),
                        "<<<" + position.getStableKey() + ">>>",
                        List.of(),
                        "single-v1",
                        List.of(),
                        "/internal/v1/books/%d/translations/%d/fragments/%d".formatted(
                                process.getBookId(),
                                process.getId(),
                                position.getSegmentId()
                        )
                )
        );
    }

    @Transactional
    public TranslationFragmentResultResponse acceptFragment(
            Long bookId,
            Long processId,
            Long segmentId,
            TranslationFragmentResultRequest request
    ) {
        TranslationProcess process = requireProcess(processId);
        if (!process.getBookId().equals(bookId)) {
            throw new IllegalArgumentException("Translation process does not belong to book");
        }
        Segment segment = segments.findById(segmentId)
                .filter(candidate -> candidate.getBook().getId().equals(bookId))
                .orElseThrow(() -> new IllegalArgumentException(
                        "Translation segment does not belong to book"
                ));
        TextSegment source = segment.getTextSegment();
        if (!segment.isTranslatable() || source == null) {
            throw new IllegalArgumentException("Segment is not translatable");
        }
        if (!source.getTextHash().equals(request.sourceHash())) {
            throw new IllegalArgumentException("Translation source hash does not match segment");
        }
        if (!requestId(processId, segmentId, request.sourceHash()).equals(request.requestId())) {
            throw new IllegalArgumentException("Translation requestId does not match segment");
        }

        TranslatedSegmentId translationId = new TranslatedSegmentId(
                source.getTextHash(),
                process.getTargetLanguage()
        );
        if (process.getStatus() == ProcessStatus.COMPLETED) {
            return new TranslationFragmentResultResponse(
                    translations.existsById(translationId),
                    ProcessStatus.COMPLETED,
                    List.of()
            );
        }
        if (process.getStatus() == ProcessStatus.FAILED) {
            return new TranslationFragmentResultResponse(
                    false,
                    ProcessStatus.FAILED,
                    List.of("PROCESS_ALREADY_FAILED")
            );
        }
        if (request.status() == TranslationResultStatus.FAILED) {
            process.fail();
            String issue = StringUtils.hasText(request.error())
                    ? request.error()
                    : "AGENT_TRANSLATION_FAILED";
            return new TranslationFragmentResultResponse(
                    false,
                    ProcessStatus.FAILED,
                    List.of(issue)
            );
        }
        if (!StringUtils.hasText(request.rawResponse())) {
            process.fail();
            return new TranslationFragmentResultResponse(
                    false,
                    ProcessStatus.FAILED,
                    List.of("AGENT_RESPONSE_EMPTY")
            );
        }

        TranslationValidationResult validation = validator.validate(
                segment.getStableKey(),
                source.getText(),
                request.rawResponse()
        );
        if (!validation.valid()) {
            process.fail();
            return new TranslationFragmentResultResponse(
                    false,
                    ProcessStatus.FAILED,
                    validation.issues()
            );
        }

        if (!translations.existsById(translationId)) {
            translations.save(
                    new TranslatedSegment(
                            source,
                            process.getTargetLanguage(),
                            validation.translation()
                    )
            );
        }
        events.publishEvent(new TranslationFragmentStoredEvent(processId));
        return new TranslationFragmentResultResponse(
                true,
                ProcessStatus.IN_PROGRESS,
                List.of()
        );
    }

    private TranslationProcess requireProcess(Long processId) {
        return processes.findById(processId)
                .orElseThrow(() -> new IllegalArgumentException(
                        "Translation process does not exist"
                ));
    }

    static String requestId(Long processId, Long segmentId, String sourceHash) {
        return UUID.nameUUIDFromBytes(
                (processId + ":" + segmentId + ":" + sourceHash)
                        .getBytes(StandardCharsets.UTF_8)
        ).toString();
    }
}
