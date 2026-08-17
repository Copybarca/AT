package io.copybarca.transapi.dto.client;

import jakarta.validation.constraints.NotNull;

public record PdfBuildRequest(@NotNull Long bookId) {
}
