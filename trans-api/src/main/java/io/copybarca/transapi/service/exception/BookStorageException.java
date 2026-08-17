package io.copybarca.transapi.service.exception;

public class BookStorageException extends RuntimeException {

    public BookStorageException(String message, Throwable cause) {
        super(message, cause);
    }
}
