package io.copybarca.transapi.controller;

import io.copybarca.transapi.dto.translation.TranslationFragmentResultRequest;
import io.copybarca.transapi.dto.translation.TranslationFragmentResultResponse;
import io.copybarca.transapi.service.InternalServiceAuthorizer;
import io.copybarca.transapi.service.TranslationPipelineService;
import jakarta.validation.Valid;
import org.springframework.http.HttpHeaders;
import org.springframework.web.bind.annotation.PathVariable;
import org.springframework.web.bind.annotation.PostMapping;
import org.springframework.web.bind.annotation.RequestBody;
import org.springframework.web.bind.annotation.RequestHeader;
import org.springframework.web.bind.annotation.RequestMapping;
import org.springframework.web.bind.annotation.RestController;

@RestController
@RequestMapping("/internal/v1/books/{bookId}/translations/{processId}/fragments")
public class InternalTranslationController {

    private final InternalServiceAuthorizer authorizer;
    private final TranslationPipelineService service;

    public InternalTranslationController(
            InternalServiceAuthorizer authorizer,
            TranslationPipelineService service
    ) {
        this.authorizer = authorizer;
        this.service = service;
    }

    @PostMapping("/{segmentId}")
    public TranslationFragmentResultResponse accept(
            @PathVariable Long bookId,
            @PathVariable Long processId,
            @PathVariable Long segmentId,
            @RequestHeader(value = HttpHeaders.AUTHORIZATION, required = false)
            String authorization,
            @Valid @RequestBody TranslationFragmentResultRequest request
    ) {
        authorizer.require(authorization);
        return service.acceptFragment(bookId, processId, segmentId, request);
    }
}
