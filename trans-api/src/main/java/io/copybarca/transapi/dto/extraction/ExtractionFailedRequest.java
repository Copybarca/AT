package io.copybarca.transapi.dto.extraction;

import jakarta.validation.constraints.NotNull;

public record ExtractionFailedRequest(@NotNull Long processId) {
}
