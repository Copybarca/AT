package io.copybarca.transapi.controller;

import io.copybarca.transapi.dto.fragment.FragmentPageResponse;
import io.copybarca.transapi.dto.fragment.FragmentResponse;
import io.copybarca.transapi.dto.fragment.SaveTranslationRequest;
import io.copybarca.transapi.service.FragmentService;
import jakarta.validation.Valid;
import org.springframework.web.bind.annotation.GetMapping;
import org.springframework.web.bind.annotation.PathVariable;
import org.springframework.web.bind.annotation.PutMapping;
import org.springframework.web.bind.annotation.RequestBody;
import org.springframework.web.bind.annotation.RequestMapping;
import org.springframework.web.bind.annotation.RequestParam;
import org.springframework.web.bind.annotation.RestController;

@RestController
@RequestMapping("/api/v1/books/{bookId}/fragments")
public class FragmentController {

    private final FragmentService service;

    public FragmentController(FragmentService service) {
        this.service = service;
    }

    @GetMapping
    public FragmentPageResponse page(
            @PathVariable Long bookId,
            @RequestParam String targetLanguage,
            @RequestParam(defaultValue = "all") String filter,
            @RequestParam(required = false) Integer afterSequence,
            @RequestParam(defaultValue = "20") int limit
    ) {
        return service.page(
                bookId,
                targetLanguage,
                filter,
                afterSequence,
                limit
        );
    }

    @PutMapping("/{fragmentId}/translation")
    public FragmentResponse save(
            @PathVariable Long bookId,
            @PathVariable Long fragmentId,
            @Valid @RequestBody SaveTranslationRequest request
    ) {
        return service.save(
                bookId,
                fragmentId,
                request.targetLanguage(),
                request.translatedText()
        );
    }
}
