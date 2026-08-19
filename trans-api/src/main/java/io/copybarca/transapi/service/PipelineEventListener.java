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
import org.springframework.transaction.event.TransactionalEventListener;

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

    public PipelineEventListener(
            TranslationProcessRepository translations,
            TranslationPipelineService translationPipeline,
            PdfBuildProcessRepository builds,
            BookRepository books,
            PdfBuildDispatchService buildDispatch,
            PipelineTaskQueue queue
    ) {
        this.translations = translations;
        this.translationPipeline = translationPipeline;
        this.builds = builds;
        this.books = books;
        this.buildDispatch = buildDispatch;
        this.queue = queue;
    }

    @TransactionalEventListener(phase = TransactionPhase.AFTER_COMMIT)
    public void afterExtraction(ExtractionCompletedEvent event) {
        for (TranslationProcess process : translations.findByBookIdAndStatus(
                event.bookId(),
                ProcessStatus.IN_PROGRESS
        )) {
            submitTranslation(process);
        }
    }

    @TransactionalEventListener(phase = TransactionPhase.AFTER_COMMIT)
    public void afterTranslation(TranslationCompletedEvent event) {
        Book book = books.findById(event.bookId()).orElseThrow();
        PdfBuildProcess process = builds.findByBookIdAndTargetLanguage(
                        event.bookId(),
                        event.targetLanguage()
                )
                .orElseGet(() -> builds.save(
                        new PdfBuildProcess(book, event.targetLanguage())
                ));
        QueueSubmitOutcome outcome = queue.submit(
                "build:" + process.getId(),
                process.getBookId() + ":" + process.getTargetLanguage(),
                () -> buildDispatch.dispatch(process.getId())
        );
        if (outcome == QueueSubmitOutcome.FULL) {
            LOGGER.warn("Build queue is full for process {}", process.getId());
        }
    }

    private void submitTranslation(TranslationProcess process) {
        QueueSubmitOutcome outcome = queue.submit(
                "translation:" + process.getId(),
                process.getBookId() + ":" + process.getTargetLanguage(),
                () -> translationPipeline.run(process.getId())
        );
        if (outcome == QueueSubmitOutcome.FULL) {
            LOGGER.warn(
                    "Translation queue is full for process {}",
                    process.getId()
            );
        }
    }
}
