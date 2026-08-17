package io.copybarca.transapi.dto.client;

import jakarta.validation.constraints.NotBlank;

public record PdfExtractRequest(@NotBlank String path) {
}
