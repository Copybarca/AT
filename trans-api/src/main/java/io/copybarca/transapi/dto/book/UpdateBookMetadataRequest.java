package io.copybarca.transapi.dto.book;

import jakarta.validation.constraints.Size;

public record UpdateBookMetadataRequest(
        @Size(min = 1, max = 128) String title,
        @Size(min = 1, max = 3) String originalLanguage
) {
}
