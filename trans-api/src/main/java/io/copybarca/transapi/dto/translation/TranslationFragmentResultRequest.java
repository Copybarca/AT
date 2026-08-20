package io.copybarca.transapi.dto.translation;

import jakarta.validation.constraints.NotBlank;
import jakarta.validation.constraints.NotNull;
import jakarta.validation.constraints.Size;

public record TranslationFragmentResultRequest(
        @NotBlank String requestId,
        @NotBlank String sourceHash,
        @NotNull TranslationResultStatus status,
        String rawResponse,
        @Size(max = 128) String model,
        Long elapsedMilliseconds,
        @Size(max = 2000) String error
) {
}
