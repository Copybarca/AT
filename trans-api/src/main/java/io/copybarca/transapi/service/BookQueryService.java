package io.copybarca.transapi.service;

import io.copybarca.transapi.dto.book.BookCountersResponse;
import io.copybarca.transapi.dto.book.BookListResponse;
import io.copybarca.transapi.dto.book.BookViewResponse;
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
import java.util.Comparator;
import java.util.List;
import java.util.Locale;
import org.springframework.stereotype.Service;
import org.springframework.transaction.annotation.Transactional;

@Service
public class BookQueryService {

    private final BookRepository books;
    private final PdfExtractionProcessRepository extractions;
    private final TranslationProcessRepository translations;
    private final PdfBuildProcessRepository builds;
    private final SegmentRepository segments;

    public BookQueryService(
            BookRepository books,
            PdfExtractionProcessRepository extractions,
            TranslationProcessRepository translations,
            PdfBuildProcessRepository builds,
            SegmentRepository segments
    ) {
        this.books = books;
        this.extractions = extractions;
        this.translations = translations;
        this.builds = builds;
        this.segments = segments;
    }

    @Transactional(readOnly = true)
    public BookListResponse list(String search, String status) {
        String query = search == null ? "" : search.trim().toLowerCase(Locale.ROOT);
        String requestedStatus = status == null ? "all" : status;
        List<BookViewResponse> all = books.findAll().stream()
                .map(this::project)
                .sorted(Comparator.comparing(BookViewResponse::id).reversed())
                .toList();
        BookCountersResponse counters = new BookCountersResponse(
                all.size(),
                (int) all.stream().filter(item -> bucket(item).equals("progress")).count(),
                (int) all.stream().filter(item -> bucket(item).equals("done")).count(),
                (int) all.stream().filter(item -> bucket(item).equals("failed")).count()
        );
        List<BookViewResponse> filtered = all.stream()
                .filter(item -> query.isEmpty()
                        || item.title().toLowerCase(Locale.ROOT).contains(query))
                .filter(item -> requestedStatus.equals("all")
                        || bucket(item).equals(requestedStatus))
                .toList();
        return new BookListResponse(filtered, counters);
    }

    @Transactional(readOnly = true)
    public BookViewResponse get(Long bookId) {
        return books.findById(bookId)
                .map(this::project)
                .orElseThrow(() -> new BookNotFoundException(bookId));
    }

    private BookViewResponse project(Book book) {
        PdfExtractionProcess extraction = extractions.findByBook_Id(book.getId())
                .orElse(null);
        String language = book.getTargetLanguage();
        TranslationProcess translation = language == null ? null
                : translations.findByBook_IdAndTargetLanguage(book.getId(), language)
                        .orElse(null);
        PdfBuildProcess build = language == null ? null
                : builds.findByBook_IdAndTargetLanguage(book.getId(), language)
                        .orElse(null);
        TranslationProgress progress = language == null ? null
                : segments.translationProgress(book.getId(), language);
        return new BookViewResponse(
                book.getId(),
                book.getTitle(),
                filename(book),
                book.getOriginalLanguage(),
                language,
                contentStatus(book, extraction),
                processStatus(translation),
                pdfStatus(book, build),
                progress == null ? 0 : progress.getTotalFragments(),
                progress == null ? 0 : progress.getTranslatedFragments(),
                segments.countImagePositions(book.getId()),
                book.getUpdatedAt()
        );
    }

    private static String contentStatus(Book book, PdfExtractionProcess process) {
        if (book.getTranslatedPath() != null
                || process != null && process.getStatus() == ProcessStatus.COMPLETED) {
            return "complete";
        }
        if (process != null && process.getStatus() == ProcessStatus.FAILED) {
            return "failed";
        }
        return "uploading";
    }

    private static String processStatus(TranslationProcess process) {
        if (process == null) {
            return "not_started";
        }
        return process.getStatus().name().toLowerCase(Locale.ROOT);
    }

    private static String pdfStatus(Book book, PdfBuildProcess process) {
        if (book.getTranslatedPath() != null
                || process != null && process.getStatus() == ProcessStatus.COMPLETED) {
            return "ready";
        }
        if (process == null) {
            return "missing";
        }
        return switch (process.getStatus()) {
            case IN_PROGRESS -> "building";
            case FAILED -> "failed";
            case COMPLETED -> "ready";
        };
    }

    private static String bucket(BookViewResponse item) {
        if ("failed".equals(item.contentStatus())
                || "failed".equals(item.translationStatus())
                || "failed".equals(item.pdfStatus())) {
            return "failed";
        }
        if ("ready".equals(item.pdfStatus())) {
            return "done";
        }
        if ("uploading".equals(item.contentStatus())
                || "in_progress".equals(item.translationStatus())
                || "building".equals(item.pdfStatus())) {
            return "progress";
        }
        return "other";
    }

    private static String filename(Book book) {
        if (book.getOriginalFilename() != null) {
            return book.getOriginalFilename();
        }
        String path = book.getPath();
        return path == null ? book.getTitle() + ".pdf"
                : path.substring(path.lastIndexOf('/') + 1);
    }
}
