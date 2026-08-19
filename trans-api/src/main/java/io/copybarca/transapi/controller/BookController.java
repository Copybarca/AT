package io.copybarca.transapi.controller;

import io.copybarca.transapi.dto.book.BookResponse;
import io.copybarca.transapi.dto.book.CreateBookRequest;
import io.copybarca.transapi.dto.book.UpdateBookMetadataRequest;
import io.copybarca.transapi.service.BookService;
import jakarta.validation.Valid;
import java.net.URI;
import org.springframework.http.MediaType;
import org.springframework.http.ResponseEntity;
import org.springframework.web.bind.annotation.DeleteMapping;
import org.springframework.web.bind.annotation.PatchMapping;
import org.springframework.web.bind.annotation.PathVariable;
import org.springframework.web.bind.annotation.PostMapping;
import org.springframework.web.bind.annotation.RequestParam;
import org.springframework.web.bind.annotation.RequestBody;
import org.springframework.web.bind.annotation.RequestMapping;
import org.springframework.web.bind.annotation.RequestPart;
import org.springframework.web.bind.annotation.RestController;
import org.springframework.web.multipart.MultipartFile;

@RestController
@RequestMapping("/api/v1/books")
public class BookController {

    private final BookService bookService;

    public BookController(BookService bookService) {
        this.bookService = bookService;
    }

    @PostMapping(consumes = MediaType.APPLICATION_JSON_VALUE)
    public ResponseEntity<BookResponse> addBook(@Valid @RequestBody CreateBookRequest request) {
        BookResponse response = bookService.addBook(request);
        return ResponseEntity
                .created(URI.create("/api/v1/books/" + response.id()))
                .body(response);

    }
    @PostMapping(consumes = MediaType.MULTIPART_FORM_DATA_VALUE)
    public ResponseEntity<BookResponse> addBookWithOriginal(
            @RequestPart("file") MultipartFile file,
            @RequestParam(required = false) String title,
            @RequestParam String originalLanguage
    ) {
        BookResponse response = bookService.createBook(
                file,
                title,
                originalLanguage
        );
        return ResponseEntity
                .created(URI.create("/api/v1/books/" + response.id()))
                .body(response);
    }

    @PatchMapping("/{bookId}")
    public BookResponse updateBookMetadata(
            @PathVariable Long bookId,
            @Valid @RequestBody UpdateBookMetadataRequest request
    ) {
        return bookService.updateMetadata(bookId, request);
    }

    @DeleteMapping("/{bookId}")
    public ResponseEntity<Void> deleteBook(@PathVariable Long bookId) {
        bookService.deleteBook(bookId);
        return ResponseEntity.noContent().build();
    }

    @PostMapping(path = "/{bookId}/original", consumes = MediaType.MULTIPART_FORM_DATA_VALUE)
    public BookResponse addOriginalBookData(
            @PathVariable Long bookId,
            @RequestPart("file") MultipartFile file
    ) {
        return bookService.addOriginalBookData(bookId, file);
    }

    @PostMapping(path = "/{bookId}/translated", consumes = MediaType.MULTIPART_FORM_DATA_VALUE)
    public BookResponse addTranslatedBook(
            @PathVariable Long bookId,
            @RequestPart("file") MultipartFile file
    ) {
        return bookService.addTranslatedBook(bookId, file);
    }
}
