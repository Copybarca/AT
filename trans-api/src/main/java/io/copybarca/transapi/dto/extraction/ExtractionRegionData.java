package io.copybarca.transapi.dto.extraction;

import jakarta.validation.constraints.Min;
import jakarta.validation.constraints.NotBlank;
import jakarta.validation.constraints.NotNull;
import java.math.BigDecimal;

public record ExtractionRegionData(
        @NotBlank String imageStableKey,
        @NotBlank String stableKey,
        @NotBlank String sourceHash,
        @Min(1) int sequentialNumber,
        @Min(1) int physicalPage,
        @NotNull BoundingBoxData bbox,
        @NotBlank String text,
        BigDecimal confidence
) {
}
