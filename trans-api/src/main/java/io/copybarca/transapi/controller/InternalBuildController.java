package io.copybarca.transapi.controller;

import io.copybarca.transapi.service.BuildResultService;
import io.copybarca.transapi.service.InternalServiceAuthorizer;
import org.springframework.http.HttpHeaders;
import org.springframework.http.MediaType;
import org.springframework.http.ResponseEntity;
import org.springframework.web.bind.annotation.PathVariable;
import org.springframework.web.bind.annotation.PostMapping;
import org.springframework.web.bind.annotation.RequestBody;
import org.springframework.web.bind.annotation.RequestHeader;
import org.springframework.web.bind.annotation.RequestMapping;
import org.springframework.web.bind.annotation.RestController;

@RestController
@RequestMapping("/internal/v1/books/{bookId}")
public class InternalBuildController {

    private final InternalServiceAuthorizer authorizer;
    private final BuildResultService service;

    public InternalBuildController(
            InternalServiceAuthorizer authorizer,
            BuildResultService service
    ) {
        this.authorizer = authorizer;
        this.service = service;
    }

    @PostMapping(
            path = "/build-result",
            consumes = MediaType.APPLICATION_PDF_VALUE
    )
    public ResponseEntity<Void> accept(
            @PathVariable Long bookId,
            @RequestHeader(value = HttpHeaders.AUTHORIZATION, required = false)
            String authorization,
            @RequestHeader("X-Process-Id") Long processId,
            @RequestHeader("X-Book-Id") Long headerBookId,
            @RequestHeader("X-PDF-SHA256") String sha256,
            @RequestHeader("X-PDF-Page-Count") int pageCount,
            @RequestBody byte[] pdf
    ) {
        authorizer.require(authorization);
        if (!bookId.equals(headerBookId)) {
            throw new IllegalArgumentException("X-Book-Id does not match callback path");
        }
        service.accept(bookId, processId, sha256, pageCount, pdf);
        return ResponseEntity.noContent().build();
    }
}
