package io.copybarca.transapi.dto.fragment;

import jakarta.validation.constraints.NotBlank;

public record SaveTranslationRequest(
        @NotBlank String targetLanguage,
        @NotBlank String translatedText
) {
}
