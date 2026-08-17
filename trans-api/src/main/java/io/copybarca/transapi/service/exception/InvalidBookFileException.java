package io.copybarca.transapi.service.exception;

public class InvalidBookFileException extends RuntimeException {

    public InvalidBookFileException(String message) {
        super(message);
    }
}
