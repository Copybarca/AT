package io.copybarca.transapi.dto.process;

import jakarta.validation.constraints.NotBlank;

public record BuildDocumentRequest(
        @NotBlank String targetLanguage,
        boolean replaceExisting
) {
}
