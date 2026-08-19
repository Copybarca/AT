package io.copybarca.transapi.dto.client;

public record PdfExtractRequest(
        Long processId,
        Long bookId,
        String sourceSha256
) {
}
