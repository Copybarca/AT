package io.copybarca.transapi.dto.client;

public record TranslationDispatchAcceptedResponse(
        String requestId,
        Long processId,
        Long segmentId,
        boolean accepted
) {
}
