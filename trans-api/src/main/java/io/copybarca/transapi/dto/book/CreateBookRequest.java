package io.copybarca.transapi.dto.book;

import jakarta.validation.constraints.NotBlank;
import jakarta.validation.constraints.Size;

public record CreateBookRequest(
        @NotBlank @Size(max = 128) String title,
        @NotBlank @Size(max = 3) String originalLanguage
) {
}
