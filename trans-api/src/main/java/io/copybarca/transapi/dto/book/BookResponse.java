package io.copybarca.transapi.dto.book;

public record BookResponse(
        Long id,
        String title,
        String originalLanguage,
        String path,
        String translatedPath,
        String translatedElementPath
) {
}
