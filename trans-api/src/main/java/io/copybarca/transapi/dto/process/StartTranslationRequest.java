package io.copybarca.transapi.dto.process;

import jakarta.validation.constraints.NotBlank;
import jakarta.validation.constraints.Size;

public record StartTranslationRequest(
        @NotBlank @Size(max = 32) String targetLanguage
) {
}
