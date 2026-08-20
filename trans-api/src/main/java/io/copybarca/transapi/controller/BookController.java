package io.copybarca.transapi.controller;

import io.copybarca.transapi.dto.book.BookListResponse;
import io.copybarca.transapi.dto.book.BookResponse;
import io.copybarca.transapi.dto.book.BookViewResponse;
import io.copybarca.transapi.dto.book.CreateBookRequest;
import io.copybarca.transapi.dto.book.UpdateBookMetadataRequest;
import io.copybarca.transapi.dto.process.BuildDocumentRequest;
import io.copybarca.transapi.model.Book;
import io.copybarca.transapi.repo.BookRepository;
import io.copybarca.transapi.service.BookFileStorage;
import io.copybarca.transapi.service.BookQueryService;
import io.copybarca.transapi.service.BookService;
import io.copybarca.transapi.service.PublicBuildService;
import io.copybarca.transapi.service.exception.BookNotFoundException;
import jakarta.validation.Valid;
import java.net.URI;
import java.util.List;
import org.springframework.http.ContentDisposition;
import org.springframework.http.HttpHeaders;
import org.springframework.http.MediaType;
import org.springframework.http.ResponseEntity;
import org.springframework.web.bind.annotation.DeleteMapping;
import org.springframework.web.bind.annotation.GetMapping;
import org.springframework.web.bind.annotation.PatchMapping;
import org.springframework.web.bind.annotation.PathVariable;
import org.springframework.web.bind.annotation.PostMapping;
import org.springframework.web.bind.annotation.RequestBody;
import org.springframework.web.bind.annotation.RequestMapping;
import org.springframework.web.bind.annotation.RequestParam;
import org.springframework.web.bind.annotation.RequestPart;
import org.springframework.web.bind.annotation.RestController;
import org.springframework.web.multipart.MultipartFile;

@RestController
@RequestMapping("/api/v1/books")
public class BookController {

    private final BookService bookService;
    private final BookQueryService query;
    private final PublicBuildService buildService;
    private final BookRepository books;
    private final BookFileStorage storage;

    public BookController(
            BookService bookService,
            BookQueryService query,
            PublicBuildService buildService,
            BookRepository books,
            BookFileStorage storage
    ) {
        this.bookService = bookService;
        this.query = query;
        this.buildService = buildService;
        this.books = books;
        this.storage = storage;
    }

    @GetMapping
    public BookListResponse list(
            @RequestParam(defaultValue = "") String search,
            @RequestParam(defaultValue = "all") String status
    ) {
        return query.list(search, status);
    }

    @GetMapping("/buildable")
    public List<BookViewResponse> buildable() {
        return query.list("", "all").items().stream()
                .filter(book -> "complete".equals(book.contentStatus()))
                .toList();
    }

    @GetMapping("/{bookId}")
    public BookViewResponse get(@PathVariable Long bookId) {
        return query.get(bookId);
    }

    @PostMapping(consumes = MediaType.APPLICATION_JSON_VALUE)
    public ResponseEntity<BookResponse> addBook(
            @Valid @RequestBody CreateBookRequest request
    ) {
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
        BookResponse response = bookService.createBook(file, title, originalLanguage);
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

    @GetMapping(path = "/{bookId}/translated", produces = MediaType.APPLICATION_PDF_VALUE)
    public ResponseEntity<byte[]> downloadTranslated(
            @PathVariable Long bookId,
            @RequestParam String targetLanguage
    ) {
        Book book = books.findById(bookId)
                .orElseThrow(() -> new BookNotFoundException(bookId));
        if (book.getTranslatedPath() == null
                || !targetLanguage.equals(book.getTargetLanguage())) {
            throw new IllegalStateException("Translated PDF is not ready");
        }
        String filename = book.getTitle().replaceAll("[^\\p{L}\\p{N}._-]+", "_")
                + "-" + targetLanguage + ".pdf";
        HttpHeaders headers = new HttpHeaders();
        headers.setContentDisposition(
                ContentDisposition.attachment().filename(filename).build()
        );
        return ResponseEntity.ok()
                .headers(headers)
                .contentType(MediaType.APPLICATION_PDF)
                .body(storage.read(book.getTranslatedPath()));
    }

    @PostMapping("/{bookId}/build")
    public ResponseEntity<BookViewResponse> build(
            @PathVariable Long bookId,
            @Valid @RequestBody BuildDocumentRequest request
    ) {
        buildService.start(
                bookId,
                request.targetLanguage(),
                request.replaceExisting()
        );
        return ResponseEntity.accepted().body(query.get(bookId));
    }
}
