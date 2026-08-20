package io.copybarca.transapi.dto.book;

import java.time.Instant;

public record BookViewResponse(
        Long id,
        String title,
        String fileName,
        String sourceLanguage,
        String targetLanguage,
        String contentStatus,
        String translationStatus,
        String pdfStatus,
        long totalFragments,
        long translatedFragments,
        long imageCount,
        Instant updatedAt
) {
}
