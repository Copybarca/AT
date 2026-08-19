package io.copybarca.transapi.service;

public record TranslationCompletedEvent(
        Long processId,
        Long bookId,
        String targetLanguage
) {
}
