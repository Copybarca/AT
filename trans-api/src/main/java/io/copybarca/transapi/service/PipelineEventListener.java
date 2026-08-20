package io.copybarca.transapi.service;

import io.copybarca.transapi.model.Book;
import io.copybarca.transapi.model.PdfBuildProcess;
import io.copybarca.transapi.model.ProcessStatus;
import io.copybarca.transapi.model.TranslationProcess;
import io.copybarca.transapi.repo.BookRepository;
import io.copybarca.transapi.repo.PdfBuildProcessRepository;
import io.copybarca.transapi.repo.TranslationProcessRepository;
import org.slf4j.Logger;
import org.slf4j.LoggerFactory;
import org.springframework.stereotype.Component;
import org.springframework.transaction.event.TransactionPhase;
import org.springframework.transaction.annotation.Propagation;
import org.springframework.transaction.annotation.Transactional;
import org.springframework.transaction.event.TransactionalEventListener;
import org.springframework.transaction.support.TransactionSynchronization;
import org.springframework.transaction.support.TransactionSynchronizationManager;

@Component
public class PipelineEventListener {

    private static final Logger LOGGER = LoggerFactory.getLogger(
            PipelineEventListener.class
    );

    private final TranslationProcessRepository translations;
    private final TranslationPipelineService translationPipeline;
    private final PdfBuildProcessRepository builds;
    private final BookRepository books;
    private final PdfBuildDispatchService buildDispatch;
    private final PipelineTaskQueue queue;
    private final PipelineFailureService failures;

    public PipelineEventListener(
            TranslationProcessRepository translations,
            TranslationPipelineService translationPipeline,
            PdfBuildProcessRepository builds,
            BookRepository books,
            PdfBuildDispatchService buildDispatch,
            PipelineTaskQueue queue,
            PipelineFailureService failures
    ) {
        this.translations = translations;
        this.translationPipeline = translationPipeline;
        this.builds = builds;
        this.books = books;
        this.buildDispatch = buildDispatch;
        this.queue = queue;
        this.failures = failures;
    }

    @TransactionalEventListener(phase = TransactionPhase.AFTER_COMMIT)
    public void afterExtraction(ExtractionCompletedEvent event) {
        for (TranslationProcess process : translations.findByBook_IdAndStatus(
                event.bookId(),
                ProcessStatus.IN_PROGRESS
        )) {
            submitTranslation(process);
        }
    }

    @TransactionalEventListener(phase = TransactionPhase.AFTER_COMMIT)
    @Transactional(propagation = Propagation.REQUIRES_NEW)
    public void afterTranslation(TranslationCompletedEvent event) {
        Book book = books.findById(event.bookId()).orElseThrow();
        PdfBuildProcess process = builds.findByBook_IdAndTargetLanguage(
                        event.bookId(),
                        event.targetLanguage()
                )
                .orElseGet(() -> builds.saveAndFlush(
                        new PdfBuildProcess(book, event.targetLanguage())
                ));
        Long processId = process.getId();
        Long bookId = process.getBookId();
        String targetLanguage = process.getTargetLanguage();
        if (TransactionSynchronizationManager.isSynchronizationActive()) {
            TransactionSynchronizationManager.registerSynchronization(
                    new TransactionSynchronization() {
                        @Override
                        public void afterCommit() {
                            submitBuild(processId, bookId, targetLanguage);
                        }
                    }
            );
        } else {
            submitBuild(processId, bookId, targetLanguage);
        }
    }

    private void submitBuild(Long processId, Long bookId, String targetLanguage) {
        QueueSubmitOutcome outcome = queue.submit(
                "build:" + processId,
                bookId + ":" + targetLanguage,
                () -> buildDispatch.dispatch(processId),
                ignored -> failures.failBuild(processId)
        );
        if (outcome == QueueSubmitOutcome.FULL) {
            LOGGER.warn("Build queue is full for process {}", processId);
        }
    }

    @TransactionalEventListener(phase = TransactionPhase.AFTER_COMMIT)
    public void afterTranslationFragment(TranslationFragmentStoredEvent event) {
        translations.findById(event.processId())
                .filter(process -> process.getStatus() == ProcessStatus.IN_PROGRESS)
                .ifPresent(this::submitTranslation);
    }

    private void submitTranslation(TranslationProcess process) {
        QueueSubmitOutcome outcome = queue.submit(
                "translation:" + process.getId(),
                process.getBookId() + ":" + process.getTargetLanguage(),
                () -> translationPipeline.run(process.getId()),
                ignored -> failures.failTranslation(process.getId())
        );
        if (outcome == QueueSubmitOutcome.FULL) {
            LOGGER.warn(
                    "Translation queue is full for process {}",
                    process.getId()
            );
        }
    }
}
