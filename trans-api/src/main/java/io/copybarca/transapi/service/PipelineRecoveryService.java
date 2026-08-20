package io.copybarca.transapi.service;

import io.copybarca.transapi.model.Book;
import io.copybarca.transapi.model.PdfBuildProcess;
import io.copybarca.transapi.model.PdfExtractionProcess;
import io.copybarca.transapi.model.ProcessStatus;
import io.copybarca.transapi.model.TranslationProcess;
import io.copybarca.transapi.repo.BookRepository;
import io.copybarca.transapi.repo.PdfBuildProcessRepository;
import io.copybarca.transapi.repo.PdfExtractionProcessRepository;
import io.copybarca.transapi.repo.TranslationProcessRepository;
import org.springframework.boot.ApplicationArguments;
import org.springframework.boot.ApplicationRunner;
import org.springframework.stereotype.Component;

@Component
public class PipelineRecoveryService implements ApplicationRunner {

    private final PdfExtractionProcessRepository extractions;
    private final TranslationProcessRepository translations;
    private final PdfBuildProcessRepository builds;
    private final BookRepository books;
    private final PdfExtractionDispatchService extractionDispatch;
    private final TranslationPipelineService translationPipeline;
    private final PdfBuildDispatchService buildDispatch;
    private final PipelineTaskQueue queue;
    private final PipelineFailureService failures;

    public PipelineRecoveryService(
            PdfExtractionProcessRepository extractions,
            TranslationProcessRepository translations,
            PdfBuildProcessRepository builds,
            BookRepository books,
            PdfExtractionDispatchService extractionDispatch,
            TranslationPipelineService translationPipeline,
            PdfBuildDispatchService buildDispatch,
            PipelineTaskQueue queue,
            PipelineFailureService failures
    ) {
        this.extractions = extractions;
        this.translations = translations;
        this.builds = builds;
        this.books = books;
        this.extractionDispatch = extractionDispatch;
        this.translationPipeline = translationPipeline;
        this.buildDispatch = buildDispatch;
        this.queue = queue;
        this.failures = failures;
    }

    @Override
    public void run(ApplicationArguments arguments) {
        for (PdfExtractionProcess process : extractions.findByStatus(
                ProcessStatus.IN_PROGRESS
        )) {
            Book book = books.findById(process.getBookId()).orElseThrow();
            queue.submit(
                    "extraction:" + process.getId(),
                    process.getBookId() + ":" + book.getPath(),
                    () -> extractionDispatch.dispatch(
                            process.getId(),
                            process.getBookId(),
                            book.getPath()
                    ),
                    ignored -> failures.failExtraction(process.getId())
            );
        }
        for (TranslationProcess process : translations.findByStatus(
                ProcessStatus.IN_PROGRESS
        )) {
            if (extractions.findByBook_Id(process.getBookId())
                    .filter(extraction ->
                            extraction.getStatus() == ProcessStatus.COMPLETED
                    )
                    .isPresent()) {
                queue.submit(
                        "translation:" + process.getId(),
                        process.getBookId() + ":" + process.getTargetLanguage(),
                        () -> translationPipeline.run(process.getId()),
                        ignored -> failures.failTranslation(process.getId())
                );
            }
        }
        for (PdfBuildProcess process : builds.findByStatus(
                ProcessStatus.IN_PROGRESS
        )) {
            queue.submit(
                    "build:" + process.getId(),
                    process.getBookId() + ":" + process.getTargetLanguage(),
                    () -> buildDispatch.dispatch(process.getId()),
                    ignored -> failures.failBuild(process.getId())
            );
        }
    }
}
