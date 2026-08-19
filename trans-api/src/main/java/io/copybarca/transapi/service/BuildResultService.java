package io.copybarca.transapi.service;

import io.copybarca.transapi.model.Book;
import io.copybarca.transapi.model.PdfBuildProcess;
import io.copybarca.transapi.model.ProcessStatus;
import io.copybarca.transapi.repo.BookRepository;
import io.copybarca.transapi.repo.PdfBuildProcessRepository;
import java.security.MessageDigest;
import java.security.NoSuchAlgorithmException;
import java.util.HexFormat;
import org.springframework.stereotype.Service;
import org.springframework.transaction.annotation.Transactional;

@Service
public class BuildResultService {

    private final PdfBuildProcessRepository processes;
    private final BookRepository books;
    private final BookFileStorage storage;

    public BuildResultService(
            PdfBuildProcessRepository processes,
            BookRepository books,
            BookFileStorage storage
    ) {
        this.processes = processes;
        this.books = books;
        this.storage = storage;
    }

    @Transactional
    public void accept(
            Long bookId,
            Long processId,
            String expectedSha256,
            int pageCount,
            byte[] pdf
    ) {
        PdfBuildProcess process = processes.findById(processId)
                .filter(candidate -> candidate.getBookId().equals(bookId))
                .orElseThrow(() -> new IllegalArgumentException(
                        "Build process does not belong to book"
                ));
        if (process.getStatus() == ProcessStatus.COMPLETED) {
            return;
        }
        if (pdf.length < 5
                || pdf[0] != '%'
                || pdf[1] != 'P'
                || pdf[2] != 'D'
                || pdf[3] != 'F'
                || pdf[4] != '-') {
            throw new IllegalArgumentException("Build result is not a PDF");
        }
        if (pageCount < 1) {
            throw new IllegalArgumentException("Build result page count must be positive");
        }
        String actualSha256 = sha256(pdf);
        if (!actualSha256.equals(expectedSha256)) {
            throw new IllegalArgumentException("Build result checksum does not match");
        }

        Book book = books.findById(bookId).orElseThrow();
        book.setTranslatedPath(storage.storeTranslated(bookId, pdf));
        process.complete();
    }

    private static String sha256(byte[] value) {
        try {
            MessageDigest digest = MessageDigest.getInstance("SHA-256");
            return "sha256:" + HexFormat.of().formatHex(digest.digest(value));
        } catch (NoSuchAlgorithmException exception) {
            throw new IllegalStateException("SHA-256 is not available", exception);
        }
    }
}
