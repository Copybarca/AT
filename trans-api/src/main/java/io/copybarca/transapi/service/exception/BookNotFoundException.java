package io.copybarca.transapi.service.exception;

public class BookNotFoundException extends RuntimeException {

    public BookNotFoundException(Long bookId) {
        super("Book %d was not found".formatted(bookId));
    }
}
