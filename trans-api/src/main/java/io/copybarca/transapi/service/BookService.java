package io.copybarca.transapi.service;

import io.copybarca.transapi.dto.book.BookResponse;
import io.copybarca.transapi.dto.book.CreateBookRequest;
import io.copybarca.transapi.dto.book.UpdateBookMetadataRequest;
import io.copybarca.transapi.repo.BookRepository;
import io.copybarca.transapi.repo.entity.BookEntity;
import io.copybarca.transapi.service.exception.BookNotFoundException;
import io.copybarca.transapi.service.exception.InvalidBookFileException;
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
    public BookResponse addBook(CreateBookRequest request) {
        var book = new BookEntity(request.title().trim(), request.originalLanguage().trim());
        return toResponse(bookRepository.save(book));
    }

    @Transactional
    public BookResponse updateMetadata(Long bookId, UpdateBookMetadataRequest request) {
        if (request.title() == null && request.originalLanguage() == null) {
            throw new IllegalArgumentException("At least one metadata field must be provided");
        }

        BookEntity book = findBook(bookId);
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
        BookEntity book = findBook(bookId);
        bookRepository.delete(book);
    }

    @Transactional
    public BookResponse addOriginalBookData(Long bookId, MultipartFile file) {
        requireNonEmpty(file);
        BookEntity book = findBook(bookId);
        book.setPath(bookFileStorage.storeOriginal(bookId, file));
        return toResponse(book);
    }

    @Transactional
    public BookResponse addTranslatedBook(Long bookId, MultipartFile file) {
        requireNonEmpty(file);
        requirePdf(file);
        BookEntity book = findBook(bookId);
        book.setTranslatedPath(bookFileStorage.storeTranslated(bookId, file));
        return toResponse(book);
    }

    private BookEntity findBook(Long bookId) {
        return bookRepository.findById(bookId)
                .orElseThrow(() -> new BookNotFoundException(bookId));
    }

    private static void requireNonEmpty(MultipartFile file) {
        if (file == null || file.isEmpty()) {
            throw new InvalidBookFileException("Book file must not be empty");
        }
    }

    private static void requirePdf(MultipartFile file) {
        String filename = file.getOriginalFilename();
        boolean pdfName = filename != null && filename.toLowerCase(Locale.ROOT).endsWith(".pdf");
        boolean pdfContentType = MediaType.APPLICATION_PDF_VALUE.equalsIgnoreCase(file.getContentType());
        if (!pdfName && !pdfContentType) {
            throw new InvalidBookFileException("Translated book must be a PDF document");
        }
    }

    private static BookResponse toResponse(BookEntity book) {
        return new BookResponse(
                book.getId(),
                book.getTitle(),
                book.getOriginalLanguage(),
                book.getPath(),
                book.getTranslatedPath()
        );
    }
}
