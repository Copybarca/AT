package io.copybarca.transapi.dto.extraction;

import jakarta.validation.constraints.Min;
import jakarta.validation.constraints.NotBlank;
import jakarta.validation.constraints.NotNull;

public record ExtractionCompleteRequest(
        @NotNull Long processId,
        @NotBlank String pdfSha256,
        @NotBlank String extractorVersion,
        @Min(0) int expectedSegmentCount,
        @Min(0) int expectedImageCount,
        @Min(0) int expectedRegionCount
) {
}
