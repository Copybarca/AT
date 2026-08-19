package io.copybarca.transapi.service;

public record ExtractionCompletedEvent(Long processId, Long bookId) {
}
