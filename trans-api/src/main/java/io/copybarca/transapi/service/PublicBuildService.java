package io.copybarca.transapi.service;

import io.copybarca.transapi.model.Book;
import io.copybarca.transapi.model.PdfBuildProcess;
import io.copybarca.transapi.model.ProcessStatus;
import io.copybarca.transapi.repo.BookRepository;
import io.copybarca.transapi.repo.PdfBuildProcessRepository;
import io.copybarca.transapi.repo.PdfExtractionProcessRepository;
import io.copybarca.transapi.repo.TranslationProcessRepository;
import io.copybarca.transapi.service.exception.BookNotFoundException;
import org.springframework.stereotype.Service;
import org.springframework.transaction.annotation.Transactional;
import org.springframework.transaction.support.TransactionSynchronization;
import org.springframework.transaction.support.TransactionSynchronizationManager;
import org.springframework.util.StringUtils;

@Service
public class PublicBuildService {

    private final BookRepository books;
    private final PdfExtractionProcessRepository extractions;
    private final TranslationProcessRepository translations;
    private final PdfBuildProcessRepository builds;
    private final PipelineTaskQueue queue;
    private final PdfBuildDispatchService dispatcher;
    private final PipelineFailureService failures;

    public PublicBuildService(
            BookRepository books,
            PdfExtractionProcessRepository extractions,
            TranslationProcessRepository translations,
            PdfBuildProcessRepository builds,
            PipelineTaskQueue queue,
            PdfBuildDispatchService dispatcher,
            PipelineFailureService failures
    ) {
        this.books = books;
        this.extractions = extractions;
        this.translations = translations;
        this.builds = builds;
        this.queue = queue;
        this.dispatcher = dispatcher;
        this.failures = failures;
    }

    @Transactional
    public void start(Long bookId, String targetLanguage, boolean replaceExisting) {
        if (!StringUtils.hasText(targetLanguage)) {
            throw new IllegalArgumentException("Target language is required");
        }
        String language = targetLanguage.trim();
        Book book = books.findById(bookId)
                .orElseThrow(() -> new BookNotFoundException(bookId));
        boolean extractionComplete = extractions.findByBook_Id(bookId)
                .map(process -> process.getStatus() == ProcessStatus.COMPLETED)
                .orElse(false);
        boolean translationComplete = translations
                .findByBook_IdAndTargetLanguage(bookId, language)
                .map(process -> process.getStatus() == ProcessStatus.COMPLETED)
                .orElse(false);
        if (!extractionComplete || !translationComplete) {
            throw new IllegalStateException(
                    "Build requires completed extraction and translation"
            );
        }

        PdfBuildProcess process = builds.findByBook_IdAndTargetLanguage(bookId, language)
                .orElseGet(() -> builds.save(new PdfBuildProcess(book, language)));
        if (process.getStatus() == ProcessStatus.COMPLETED) {
            if (!replaceExisting) {
                throw new IllegalStateException(
                        "Existing PDF requires confirmed rebuild"
                );
            }
            process.restart();
            book.setTranslatedPath(null);
        } else if (process.getStatus() == ProcessStatus.FAILED) {
            process.restart();
        }
        Long processId = process.getId();
        scheduleAfterCommit(() -> {
            QueueSubmitOutcome outcome = queue.submit(
                    "build:" + processId,
                    bookId + ":" + language,
                    () -> dispatcher.dispatch(processId),
                    ignored -> failures.failBuild(processId)
            );
            if (outcome == QueueSubmitOutcome.FULL) {
                failures.failBuild(processId);
            }
        });
    }

    private static void scheduleAfterCommit(Runnable action) {
        if (!TransactionSynchronizationManager.isSynchronizationActive()) {
            action.run();
            return;
        }
        TransactionSynchronizationManager.registerSynchronization(
                new TransactionSynchronization() {
                    @Override
                    public void afterCommit() {
                        action.run();
                    }
                }
        );
    }
}
