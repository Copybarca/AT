package io.copybarca.transapi.dto.extraction;

import jakarta.validation.constraints.Min;
import jakarta.validation.constraints.NotBlank;
import jakarta.validation.constraints.NotNull;

public record ExtractionSegmentData(
        @NotBlank String stableKey,
        @NotBlank String sourceHash,
        @Min(1) int sequentialNumber,
        @Min(1) int physicalPage,
        @NotNull BoundingBoxData bbox,
        @NotBlank String style,
        @NotBlank String text,
        boolean translatable
) {
}
