package io.copybarca.transapi.dto.client;

import jakarta.validation.constraints.NotBlank;

public record TranslateTextRequest(@NotBlank String text) {
}
