package io.copybarca.transapi.controller;

import io.copybarca.transapi.dto.process.BookProcessesResponse;
import io.copybarca.transapi.dto.process.StartTranslationRequest;
import io.copybarca.transapi.dto.process.TranslationAcceptedResponse;
import io.copybarca.transapi.service.PipelineProcessService;
import jakarta.validation.Valid;
import org.springframework.http.ResponseEntity;
import org.springframework.web.bind.annotation.GetMapping;
import org.springframework.web.bind.annotation.PathVariable;
import org.springframework.web.bind.annotation.PostMapping;
import org.springframework.web.bind.annotation.RequestBody;
import org.springframework.web.bind.annotation.RequestMapping;
import org.springframework.web.bind.annotation.RequestParam;
import org.springframework.web.bind.annotation.RestController;

@RestController
@RequestMapping("/api/v1/books/{bookId}")
public class TranslationController {

    private final PipelineProcessService service;

    public TranslationController(PipelineProcessService service) {
        this.service = service;
    }

    @PostMapping("/translations")
    public ResponseEntity<TranslationAcceptedResponse> start(
            @PathVariable Long bookId,
            @Valid @RequestBody StartTranslationRequest request
    ) {
        return ResponseEntity.accepted().body(
                service.start(bookId, request.targetLanguage())
        );
    }

    @GetMapping("/processes")
    public BookProcessesResponse monitor(
            @PathVariable Long bookId,
            @RequestParam String targetLanguage
    ) {
        return service.monitor(bookId, targetLanguage);
    }
}
