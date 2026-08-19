package io.copybarca.transapi.dto.extraction;

import jakarta.validation.constraints.Min;
import jakarta.validation.constraints.NotBlank;
import jakarta.validation.constraints.NotNull;

public record ExtractionImageRequest(
        @NotNull Long processId,
        @NotBlank String stableKey,
        @Min(1) int sequentialNumber,
        @Min(1) int physicalPage,
        @NotNull BoundingBoxData bbox,
        @NotBlank String mediaType
) {
}
