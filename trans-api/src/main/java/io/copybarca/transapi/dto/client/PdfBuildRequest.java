package io.copybarca.transapi.dto.client;

import java.util.List;

public record PdfBuildRequest(
        Long processId,
        Long bookId,
        String resultCallbackUrl,
        PdfBuildDocument document,
        List<PdfBuildElement> elements
) {
}
