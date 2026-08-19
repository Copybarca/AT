package io.copybarca.transapi.service;

import static org.junit.jupiter.api.Assertions.assertEquals;
import static org.junit.jupiter.api.Assertions.assertThrows;
import static org.mockito.ArgumentMatchers.any;
import static org.mockito.Mockito.verify;
import static org.mockito.Mockito.when;

import io.copybarca.transapi.dto.book.CreateBookRequest;
import io.copybarca.transapi.dto.book.UpdateBookMetadataRequest;
import io.copybarca.transapi.model.Book;
import io.copybarca.transapi.repo.BookRepository;
import io.copybarca.transapi.service.exception.InvalidBookFileException;
import java.util.Optional;
import org.junit.jupiter.api.BeforeEach;
import org.junit.jupiter.api.Test;
import org.junit.jupiter.api.extension.ExtendWith;
import org.mockito.Mock;
import org.mockito.junit.jupiter.MockitoExtension;
import org.springframework.mock.web.MockMultipartFile;

@ExtendWith(MockitoExtension.class)
class BookServiceTest {

    @Mock
    private BookRepository bookRepository;

    @Mock
    private BookFileStorage bookFileStorage;

    private BookService bookService;

    @BeforeEach
    void setUp() {
        bookService = new BookService(bookRepository, bookFileStorage);
    }

    @Test
    void addsBook() {
        when(bookRepository.save(any(Book.class))).thenAnswer(invocation -> {
            Book book = invocation.getArgument(0);
            book.setId(10L);
            return book;
        });

        var response = bookService.addBook(new CreateBookRequest("Book", "eng"));

        assertEquals(10L, response.id());
        assertEquals("Book", response.title());
        assertEquals("eng", response.originalLanguage());
    }

    @Test
    void patchesBookMetadata() {
        Book book = book(7L);
        when(bookRepository.findById(7L)).thenReturn(Optional.of(book));

        var response = bookService.updateMetadata(
                7L,
                new UpdateBookMetadataRequest("Updated", null)
        );

        assertEquals("Updated", response.title());
        assertEquals("eng", response.originalLanguage());
    }

    @Test
    void uploadsOriginalFileOfAnyFormat() {
        Book book = book(7L);
        var file = new MockMultipartFile("file", "book.epub", "application/epub+zip", "data".getBytes());
        when(bookRepository.findById(7L)).thenReturn(Optional.of(book));
        when(bookFileStorage.storeOriginal(7L, file)).thenReturn("s3://books/7/original/book.epub");

        var response = bookService.addOriginalBookData(7L, file);

        assertEquals("s3://books/7/original/book.epub", response.path());
    }

    @Test
    void rejectsNonPdfTranslatedFile() {
        var file = new MockMultipartFile("file", "book.txt", "text/plain", "data".getBytes());

        assertThrows(InvalidBookFileException.class, () -> bookService.addTranslatedBook(7L, file));
    }

    @Test
    void deletesBookMetadata() {
        Book book = book(7L);
        when(bookRepository.findById(7L)).thenReturn(Optional.of(book));

        bookService.deleteBook(7L);

        verify(bookRepository).delete(book);
    }

    @Test
    void createsBookAndStoresOriginalPdfInOneOperation() {
        var file = new MockMultipartFile(
                "file",
                "manual.pdf",
                "application/pdf",
                "%PDF-1.7\nsynthetic".getBytes()
        );
        when(bookRepository.save(any(Book.class))).thenAnswer(invocation -> {
            Book book = invocation.getArgument(0);
            book.setId(12L);
            return book;
        });
        when(bookFileStorage.storeOriginal(12L, file))
                .thenReturn("s3://trans-books/books/12/original/manual.pdf");

        var response = bookService.createBook(file, null, "eng");

        assertEquals(12L, response.id());
        assertEquals("manual", response.title());
        assertEquals("eng", response.originalLanguage());
        assertEquals(
                "s3://trans-books/books/12/original/manual.pdf",
                response.path()
        );
    }

    @Test
    void rejectsFakePdfEvenWhenFilenameAndMediaTypeClaimPdf() {
        var file = new MockMultipartFile(
                "file",
                "fake.pdf",
                "application/pdf",
                "not a pdf".getBytes()
        );

        assertThrows(
                InvalidBookFileException.class,
                () -> bookService.createBook(file, "Fake", "eng")
        );
    }

    private static Book book(Long id) {
        var book = new Book("Book", "eng");
        book.setId(id);
        return book;
    }
}
