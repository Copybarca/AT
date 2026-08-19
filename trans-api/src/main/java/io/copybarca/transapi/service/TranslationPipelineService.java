package io.copybarca.transapi.service;

import io.copybarca.transapi.dto.client.TranslateTextRequest;
import io.copybarca.transapi.dto.client.TranslateTextResponse;
import io.copybarca.transapi.model.TextSegment;
import io.copybarca.transapi.model.TranslatedSegment;
import io.copybarca.transapi.model.TranslationProcess;
import io.copybarca.transapi.repo.SegmentRepository;
import io.copybarca.transapi.repo.TextSegmentRepository;
import io.copybarca.transapi.repo.TranslatablePosition;
import io.copybarca.transapi.repo.TranslatedSegmentRepository;
import io.copybarca.transapi.repo.TranslationProcessRepository;
import io.copybarca.transapi.restclient.AgentFlowClient;
import java.util.List;
import java.util.UUID;
import org.springframework.context.ApplicationEventPublisher;
import org.springframework.stereotype.Service;
import org.springframework.transaction.annotation.Transactional;

@Service
public class TranslationPipelineService {

    private static final List<String> STRATEGIES = List.of(
            "single-v1",
            "corrective-v1",
            "protected-numbers-v1"
    );

    private final TranslationProcessRepository processes;
    private final SegmentRepository segments;
    private final TextSegmentRepository texts;
    private final TranslatedSegmentRepository translations;
    private final AgentFlowClient agent;
    private final TranslationResponseValidator validator;
    private final ApplicationEventPublisher events;

    public TranslationPipelineService(
            TranslationProcessRepository processes,
            SegmentRepository segments,
            TextSegmentRepository texts,
            TranslatedSegmentRepository translations,
            AgentFlowClient agent,
            TranslationResponseValidator validator,
            ApplicationEventPublisher events
    ) {
        this.processes = processes;
        this.segments = segments;
        this.texts = texts;
        this.translations = translations;
        this.agent = agent;
        this.validator = validator;
        this.events = events;
    }

    @Transactional
    public void run(Long processId) {
        TranslationProcess process = processes.findById(processId)
                .orElseThrow(() -> new IllegalArgumentException(
                        "Translation process does not exist"
                ));
        while (true) {
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
            translatePosition(process, position);
        }
    }

    private void translatePosition(
            TranslationProcess process,
            TranslatablePosition position
    ) {
        List<String> previousIssues = List.of();
        String marker = "<<<" + position.getStableKey() + ">>>";
        for (String strategy : STRATEGIES) {
            String requestId = UUID.randomUUID().toString();
            TranslateTextResponse response = agent.translate(
                    new TranslateTextRequest(
                            requestId,
                            position.getStableKey(),
                            position.getSourceHash(),
                            position.getSourceLanguage(),
                            process.getTargetLanguage(),
                            position.getSourceText(),
                            marker,
                            List.of(),
                            strategy,
                            previousIssues
                    )
            );
            if (!requestId.equals(response.requestId())) {
                throw new IllegalArgumentException(
                        "Translation response requestId does not match"
                );
            }
            TranslationValidationResult validation = validator.validate(
                    position.getStableKey(),
                    position.getSourceText(),
                    response.rawResponse()
            );
            if (validation.valid()) {
                TextSegment source = texts.findById(position.getSourceHash())
                        .orElseThrow();
                translations.save(
                        new TranslatedSegment(
                                source,
                                process.getTargetLanguage(),
                                validation.translation()
                        )
                );
                return;
            }
            previousIssues = validation.issues();
        }
        throw new IllegalStateException(
                "Translation content strategies exhausted for "
                        + position.getStableKey()
                        + ": "
                        + previousIssues
        );
    }
}
