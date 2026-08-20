package io.copybarca.transapi.service;

import io.copybarca.transapi.dto.process.BookProcessesResponse;
import io.copybarca.transapi.dto.process.StageStatusResponse;
import io.copybarca.transapi.dto.process.TranslationAcceptedResponse;
import io.copybarca.transapi.dto.process.TranslationStatusResponse;
import io.copybarca.transapi.model.Book;
import io.copybarca.transapi.model.PdfBuildProcess;
import io.copybarca.transapi.model.PdfExtractionProcess;
import io.copybarca.transapi.model.ProcessStatus;
import io.copybarca.transapi.model.TranslationProcess;
import io.copybarca.transapi.repo.BookRepository;
import io.copybarca.transapi.repo.PdfBuildProcessRepository;
import io.copybarca.transapi.repo.PdfExtractionProcessRepository;
import io.copybarca.transapi.repo.SegmentRepository;
import io.copybarca.transapi.repo.TranslationProcessRepository;
import io.copybarca.transapi.repo.TranslationProgress;
import io.copybarca.transapi.service.exception.BookNotFoundException;
import java.math.BigDecimal;
import java.math.RoundingMode;
import java.util.function.Supplier;
import org.slf4j.Logger;
import org.slf4j.LoggerFactory;
import org.springframework.stereotype.Service;
import org.springframework.transaction.annotation.Transactional;
import org.springframework.transaction.support.TransactionSynchronization;
import org.springframework.transaction.support.TransactionSynchronizationManager;
import org.springframework.util.StringUtils;

@Service
public class PipelineProcessService {

    private static final Logger LOGGER = LoggerFactory.getLogger(PipelineProcessService.class);

    private final BookRepository books;
    private final PdfExtractionProcessRepository extractions;
    private final TranslationProcessRepository translations;
    private final PdfBuildProcessRepository builds;
    private final SegmentRepository segments;
    private final PipelineTaskQueue queue;
    private final PdfExtractionDispatchService extractionDispatcher;
    private final TranslationPipelineService translationPipeline;
    private final PdfBuildDispatchService buildDispatcher;
    private final PipelineFailureService failures;

    public PipelineProcessService(
            BookRepository books,
            PdfExtractionProcessRepository extractions,
            TranslationProcessRepository translations,
            PdfBuildProcessRepository builds,
            SegmentRepository segments,
            PipelineTaskQueue queue,
            PdfExtractionDispatchService extractionDispatcher,
            TranslationPipelineService translationPipeline,
            PdfBuildDispatchService buildDispatcher,
            PipelineFailureService failures
    ) {
        this.books = books;
        this.extractions = extractions;
        this.translations = translations;
        this.builds = builds;
        this.segments = segments;
        this.queue = queue;
        this.extractionDispatcher = extractionDispatcher;
        this.translationPipeline = translationPipeline;
        this.buildDispatcher = buildDispatcher;
        this.failures = failures;
    }

    @Transactional
    public TranslationAcceptedResponse start(Long bookId, String targetLanguage) {
        Book book = books.findById(bookId)
                .orElseThrow(() -> new BookNotFoundException(bookId));
        if (!StringUtils.hasText(book.getPath())) {
            throw new IllegalArgumentException("Book original PDF is not stored");
        }
        String language = targetLanguage.trim();
        book.selectTargetLanguage(language);

        PdfExtractionProcess extraction = extractions.findByBook_Id(bookId)
                .orElseGet(() -> extractions.save(new PdfExtractionProcess(book)));
        TranslationProcess translation = translations
                .findByBook_IdAndTargetLanguage(bookId, language)
                .orElseGet(() -> translations.save(
                        new TranslationProcess(book, language)
                ));

        if (extraction.getStatus() == ProcessStatus.FAILED) {
            extraction.restart();
        }
        if (extraction.getStatus() == ProcessStatus.IN_PROGRESS) {
            Long processId = extraction.getId();
            String originalPath = book.getPath();
            scheduleAfterCommit(
                    "extraction",
                    processId,
                    () -> queue.submit(
                            "extraction:" + processId,
                            bookId + ":" + originalPath,
                            () -> extractionDispatcher.dispatch(
                                    processId,
                                    bookId,
                                    originalPath
                            ),
                            ignored -> failures.failExtraction(processId)
                    )
            );
        } else {
            if (translation.getStatus() == ProcessStatus.FAILED) {
                translation.restart();
            }
        }
        if (extraction.getStatus() == ProcessStatus.COMPLETED
                && translation.getStatus() == ProcessStatus.IN_PROGRESS) {
            Long processId = translation.getId();
            scheduleAfterCommit(
                    "translation",
                    processId,
                    () -> queue.submit(
                            "translation:" + processId,
                            bookId + ":" + language,
                            () -> translationPipeline.run(processId),
                            ignored -> failures.failTranslation(processId)
                    )
            );
        } else if (extraction.getStatus() == ProcessStatus.COMPLETED
                && translation.getStatus() == ProcessStatus.COMPLETED) {
            PdfBuildProcess build = builds.findByBook_IdAndTargetLanguage(bookId, language)
                    .orElseGet(() -> builds.save(new PdfBuildProcess(book, language)));
            if (build.getStatus() == ProcessStatus.FAILED) {
                build.restart();
            }
            if (build.getStatus() == ProcessStatus.IN_PROGRESS) {
                Long processId = build.getId();
                scheduleAfterCommit(
                        "build",
                        processId,
                        () -> queue.submit(
                                "build:" + processId,
                                bookId + ":" + language,
                                () -> buildDispatcher.dispatch(processId),
                                ignored -> failures.failBuild(processId)
                        )
                );
            }
        }
        return new TranslationAcceptedResponse(bookId, language);
    }

    @Transactional(readOnly = true)
    public BookProcessesResponse monitor(Long bookId, String targetLanguage) {
        if (!books.existsById(bookId)) {
            throw new BookNotFoundException(bookId);
        }
        PdfExtractionProcess extraction = extractions.findByBook_Id(bookId)
                .orElse(null);
        StageStatusResponse extractionResponse = extraction == null
                ? null
                : new StageStatusResponse(extraction.getStatus());

        TranslationStatusResponse translationResponse = null;
        TranslationProcess translation = translations
                .findByBook_IdAndTargetLanguage(bookId, targetLanguage)
                .orElse(null);
        if (extraction != null
                && extraction.getStatus() == ProcessStatus.COMPLETED
                && translation != null) {
            TranslationProgress progress = segments.translationProgress(
                    bookId,
                    targetLanguage
            );
            translationResponse = new TranslationStatusResponse(
                    translation.getStatus(),
                    progress.getTotalFragments(),
                    progress.getTranslatedFragments(),
                    percent(progress)
            );
        }

        PdfBuildProcess build = builds.findByBook_IdAndTargetLanguage(
                        bookId,
                        targetLanguage
                )
                .orElse(null);
        StageStatusResponse buildResponse = build == null
                ? null
                : new StageStatusResponse(build.getStatus());
        return new BookProcessesResponse(
                bookId,
                extractionResponse,
                translationResponse,
                buildResponse
        );
    }

    private static BigDecimal percent(TranslationProgress progress) {
        if (progress.getTotalFragments() == 0) {
            return BigDecimal.ZERO.setScale(2);
        }
        return BigDecimal.valueOf(progress.getTranslatedFragments())
                .multiply(BigDecimal.valueOf(100))
                .divide(
                        BigDecimal.valueOf(progress.getTotalFragments()),
                        2,
                        RoundingMode.HALF_UP
                );
    }

    private static void scheduleAfterCommit(
            String stage,
            Long processId,
            Supplier<QueueSubmitOutcome> submission
    ) {
        Runnable dispatch = () -> {
            QueueSubmitOutcome outcome = submission.get();
            if (outcome == QueueSubmitOutcome.FULL) {
                LOGGER.warn("{} queue is full for process {}", stage, processId);
            } else if (outcome == QueueSubmitOutcome.CONFLICT) {
                LOGGER.error("{} process {} has conflicting input", stage, processId);
            }
        };
        if (!TransactionSynchronizationManager.isSynchronizationActive()) {
            dispatch.run();
            return;
        }
        TransactionSynchronizationManager.registerSynchronization(
                new TransactionSynchronization() {
                    @Override
                    public void afterCommit() {
                        dispatch.run();
                    }
                }
        );
    }
}
