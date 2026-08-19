package io.copybarca.transapi.dto.client;

public record TranslateTextResponse(
        String requestId,
        String model,
        String rawResponse,
        long elapsedMilliseconds
) {
}
