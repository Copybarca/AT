package io.copybarca.transapi.controller;

import io.copybarca.transapi.dto.extraction.ExtractionCompleteRequest;
import io.copybarca.transapi.dto.extraction.ExtractionImageRequest;
import io.copybarca.transapi.dto.extraction.ExtractionRegionBatchRequest;
import io.copybarca.transapi.dto.extraction.ExtractionSegmentBatchRequest;
import io.copybarca.transapi.service.ExtractionResultService;
import io.copybarca.transapi.service.InternalServiceAuthorizer;
import jakarta.validation.Valid;
import org.springframework.http.HttpHeaders;
import org.springframework.http.MediaType;
import org.springframework.http.ResponseEntity;
import org.springframework.web.bind.annotation.PathVariable;
import org.springframework.web.bind.annotation.PostMapping;
import org.springframework.web.bind.annotation.RequestBody;
import org.springframework.web.bind.annotation.RequestHeader;
import org.springframework.web.bind.annotation.RequestMapping;
import org.springframework.web.bind.annotation.RequestPart;
import org.springframework.web.bind.annotation.RestController;
import org.springframework.web.multipart.MultipartFile;

@RestController
@RequestMapping("/internal/v1/books/{bookId}/extraction")
public class InternalExtractionController {

    private final InternalServiceAuthorizer authorizer;
    private final ExtractionResultService service;

    public InternalExtractionController(
            InternalServiceAuthorizer authorizer,
            ExtractionResultService service
    ) {
        this.authorizer = authorizer;
        this.service = service;
    }

    @PostMapping("/segments:batch")
    public ResponseEntity<Void> upsertSegments(
            @PathVariable Long bookId,
            @RequestHeader(value = HttpHeaders.AUTHORIZATION, required = false)
            String authorization,
            @Valid @RequestBody ExtractionSegmentBatchRequest request
    ) {
        authorizer.require(authorization);
        service.upsertSegments(bookId, request);
        return ResponseEntity.noContent().build();
    }

    @PostMapping(
            path = "/images",
            consumes = MediaType.MULTIPART_FORM_DATA_VALUE
    )
    public ResponseEntity<Void> storeImage(
            @PathVariable Long bookId,
            @RequestHeader(value = HttpHeaders.AUTHORIZATION, required = false)
            String authorization,
            @Valid @RequestPart("request") ExtractionImageRequest request,
            @RequestPart("file") MultipartFile file
    ) {
        authorizer.require(authorization);
        service.storeImage(bookId, request, file);
        return ResponseEntity.noContent().build();
    }

    @PostMapping("/image-regions:batch")
    public ResponseEntity<Void> upsertRegions(
            @PathVariable Long bookId,
            @RequestHeader(value = HttpHeaders.AUTHORIZATION, required = false)
            String authorization,
            @Valid @RequestBody ExtractionRegionBatchRequest request
    ) {
        authorizer.require(authorization);
        service.upsertRegions(bookId, request);
        return ResponseEntity.noContent().build();
    }

    @PostMapping("/complete")
    public ResponseEntity<Void> complete(
            @PathVariable Long bookId,
            @RequestHeader(value = HttpHeaders.AUTHORIZATION, required = false)
            String authorization,
            @Valid @RequestBody ExtractionCompleteRequest request
    ) {
        authorizer.require(authorization);
        service.complete(bookId, request);
        return ResponseEntity.noContent().build();
    }
}
