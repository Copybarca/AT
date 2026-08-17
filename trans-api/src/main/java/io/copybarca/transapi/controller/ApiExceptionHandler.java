package io.copybarca.transapi.controller;

import io.copybarca.transapi.service.exception.BookNotFoundException;
import io.copybarca.transapi.service.exception.BookStorageException;
import io.copybarca.transapi.service.exception.InvalidBookFileException;
import org.springframework.http.HttpStatus;
import org.springframework.http.ProblemDetail;
import org.springframework.web.bind.annotation.ExceptionHandler;
import org.springframework.web.bind.annotation.RestControllerAdvice;

@RestControllerAdvice
public class ApiExceptionHandler {

    @ExceptionHandler(BookNotFoundException.class)
    ProblemDetail handleNotFound(BookNotFoundException exception) {
        return problem(HttpStatus.NOT_FOUND, exception.getMessage());
    }

    @ExceptionHandler({InvalidBookFileException.class, IllegalArgumentException.class})
    ProblemDetail handleBadRequest(RuntimeException exception) {
        return problem(HttpStatus.BAD_REQUEST, exception.getMessage());
    }

    @ExceptionHandler(BookStorageException.class)
    ProblemDetail handleStorage(BookStorageException exception) {
        return problem(HttpStatus.BAD_GATEWAY, exception.getMessage());
    }

    private static ProblemDetail problem(HttpStatus status, String detail) {
        ProblemDetail problem = ProblemDetail.forStatusAndDetail(status, detail);
        problem.setTitle(status.getReasonPhrase());
        return problem;
    }
}
