package io.copybarca.transapi.service;

import io.copybarca.transapi.dto.book.BookResponse;
import io.copybarca.transapi.dto.book.CreateBookRequest;
import io.copybarca.transapi.dto.book.UpdateBookMetadataRequest;
import io.copybarca.transapi.model.Book;
import io.copybarca.transapi.repo.BookRepository;
import io.copybarca.transapi.service.exception.BookNotFoundException;
import io.copybarca.transapi.service.exception.InvalidBookFileException;
import java.io.IOException;
import java.io.InputStream;
import java.nio.charset.StandardCharsets;
import java.util.Locale;
import org.springframework.http.MediaType;
import org.springframework.stereotype.Service;
import org.springframework.transaction.annotation.Transactional;
import org.springframework.util.StringUtils;
import org.springframework.web.multipart.MultipartFile;

@Service
public class BookService {

    private final BookRepository bookRepository;
    private final BookFileStorage bookFileStorage;

    public BookService(BookRepository bookRepository, BookFileStorage bookFileStorage) {
        this.bookRepository = bookRepository;
        this.bookFileStorage = bookFileStorage;
    }


    @Transactional
    public BookResponse createBook(
            MultipartFile file,
            String title,
            String originalLanguage
    ) {
        requireNonEmpty(file);
        requirePdfSignature(file);
        if (!StringUtils.hasText(originalLanguage)
                || originalLanguage.trim().length() > 3) {
            throw new IllegalArgumentException(
                    "Original language must contain at most three characters"
            );
        }

        String resolvedTitle = resolveTitle(title, file.getOriginalFilename());
        Book book = bookRepository.save(
                new Book(resolvedTitle, originalLanguage.trim())
        );
        book.setPath(bookFileStorage.storeOriginal(book.getId(), file));
        return toResponse(book);
    }

    @Transactional
    public BookResponse addBook(CreateBookRequest request) {
        var book = new Book(request.title().trim(), request.originalLanguage().trim());
        return toResponse(bookRepository.save(book));
    }

    @Transactional
    public BookResponse updateMetadata(Long bookId, UpdateBookMetadataRequest request) {
        if (request.title() == null && request.originalLanguage() == null) {
            throw new IllegalArgumentException("At least one metadata field must be provided");
        }

        Book book = findBook(bookId);
        if (request.title() != null) {
            if (!StringUtils.hasText(request.title())) {
                throw new IllegalArgumentException("Book title must not be blank");
            }
            book.setTitle(request.title().trim());
        }
        if (request.originalLanguage() != null) {
            if (!StringUtils.hasText(request.originalLanguage())) {
                throw new IllegalArgumentException("Original language must not be blank");
            }
            book.setOriginalLanguage(request.originalLanguage().trim());
        }
        return toResponse(book);
    }

    @Transactional
    public void deleteBook(Long bookId) {
        Book book = findBook(bookId);
        bookRepository.delete(book);
    }

    @Transactional
    public BookResponse addOriginalBookData(Long bookId, MultipartFile file) {
        requireNonEmpty(file);
        Book book = findBook(bookId);
        book.setPath(bookFileStorage.storeOriginal(bookId, file));
        return toResponse(book);
    }

    @Transactional
    public BookResponse addTranslatedBook(Long bookId, MultipartFile file) {
        requireNonEmpty(file);
        requirePdf(file);
        Book book = findBook(bookId);
        book.setTranslatedPath(bookFileStorage.storeTranslated(bookId, file));
        return toResponse(book);
    }

    private Book findBook(Long bookId) {
        return bookRepository.findById(bookId)
                .orElseThrow(() -> new BookNotFoundException(bookId));
    }

    private static void requireNonEmpty(MultipartFile file) {
        if (file == null || file.isEmpty()) {
            throw new InvalidBookFileException("Book file must not be empty");
        }

    }
    private static void requirePdfSignature(MultipartFile file) {
        try (InputStream input = file.getInputStream()) {
            String signature = new String(
                    input.readNBytes(5),
                    StandardCharsets.US_ASCII
            );
            if (!"%PDF-".equals(signature)) {
                throw new InvalidBookFileException(
                        "Original book must have a valid PDF signature"
                );
            }
        } catch (IOException exception) {
            throw new InvalidBookFileException("Could not read original PDF");
        }
    }

    private static String resolveTitle(String title, String originalFilename) {
        String resolved = title;
        if (!StringUtils.hasText(resolved)) {
            String filename = StringUtils.hasText(originalFilename)
                    ? originalFilename.replace('\\', '/')
                    : "book.pdf";
            filename = filename.substring(filename.lastIndexOf('/') + 1);
            resolved = filename.toLowerCase(Locale.ROOT).endsWith(".pdf")
                    ? filename.substring(0, filename.length() - 4)
                    : filename;
        }
        resolved = resolved.trim();
        if (resolved.isEmpty() || resolved.length() > 128) {
            throw new IllegalArgumentException(
                    "Book title must contain between 1 and 128 characters"
            );
        }
        return resolved;
    }


    private static void requirePdf(MultipartFile file) {
        String filename = file.getOriginalFilename();
        boolean pdfName = filename != null && filename.toLowerCase(Locale.ROOT).endsWith(".pdf");
        boolean pdfContentType = MediaType.APPLICATION_PDF_VALUE.equalsIgnoreCase(file.getContentType());
        if (!pdfName && !pdfContentType) {
            throw new InvalidBookFileException("Translated book must be a PDF document");
        }
    }

    private static BookResponse toResponse(Book book) {
        return new BookResponse(
                book.getId(),
                book.getTitle(),
                book.getOriginalLanguage(),
                book.getPath(),
                book.getTranslatedPath(),
                book.getTranslatedElementPath()
        );
    }
}
