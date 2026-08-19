package io.copybarca.transapi.dto.process;

public record BookProcessesResponse(
        Long bookId,
        StageStatusResponse extraction,
        TranslationStatusResponse translation,
        StageStatusResponse pdfBuild
) {
}
