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
import org.springframework.stereotype.Service;
import org.springframework.transaction.annotation.Transactional;
import org.springframework.util.StringUtils;

@Service
public class PipelineProcessService {

    private final BookRepository books;
    private final PdfExtractionProcessRepository extractions;
    private final TranslationProcessRepository translations;
    private final PdfBuildProcessRepository builds;
    private final SegmentRepository segments;
    private final PipelineTaskQueue queue;
    private final PdfExtractionDispatchService extractionDispatcher;

    public PipelineProcessService(
            BookRepository books,
            PdfExtractionProcessRepository extractions,
            TranslationProcessRepository translations,
            PdfBuildProcessRepository builds,
            SegmentRepository segments,
            PipelineTaskQueue queue,
            PdfExtractionDispatchService extractionDispatcher
    ) {
        this.books = books;
        this.extractions = extractions;
        this.translations = translations;
        this.builds = builds;
        this.segments = segments;
        this.queue = queue;
        this.extractionDispatcher = extractionDispatcher;
    }

    @Transactional
    public TranslationAcceptedResponse start(Long bookId, String targetLanguage) {
        Book book = books.findById(bookId)
                .orElseThrow(() -> new BookNotFoundException(bookId));
        if (!StringUtils.hasText(book.getPath())) {
            throw new IllegalArgumentException("Book original PDF is not stored");
        }
        String language = targetLanguage.trim();

        PdfExtractionProcess extraction = extractions.findByBookId(bookId)
                .orElseGet(() -> extractions.save(new PdfExtractionProcess(book)));
        translations.findByBookIdAndTargetLanguage(bookId, language)
                .orElseGet(() -> translations.save(
                        new TranslationProcess(book, language)
                ));

        if (extraction.getStatus() == ProcessStatus.IN_PROGRESS) {
            QueueSubmitOutcome outcome = queue.submit(
                    "extraction:" + extraction.getId(),
                    bookId + ":" + book.getPath(),
                    () -> extractionDispatcher.dispatch(
                            extraction.getId(),
                            bookId,
                            book.getPath()
                    )
            );
            if (outcome == QueueSubmitOutcome.FULL) {
                throw new PipelineQueueFullException();
            }
            if (outcome == QueueSubmitOutcome.CONFLICT) {
                throw new IllegalStateException(
                        "Extraction process was submitted with conflicting input"
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
        PdfExtractionProcess extraction = extractions.findByBookId(bookId)
                .orElse(null);
        StageStatusResponse extractionResponse = extraction == null
                ? null
                : new StageStatusResponse(extraction.getStatus());

        TranslationStatusResponse translationResponse = null;
        TranslationProcess translation = translations
                .findByBookIdAndTargetLanguage(bookId, targetLanguage)
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

        PdfBuildProcess build = builds.findByBookIdAndTargetLanguage(
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
}
