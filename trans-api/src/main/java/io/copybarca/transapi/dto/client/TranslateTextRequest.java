package io.copybarca.transapi.dto.client;

import java.util.List;

public record TranslateTextRequest(
        String requestId,
        String stableKey,
        String sourceHash,
        String sourceLanguage,
        String targetLanguage,
        String sourceText,
        String marker,
        List<GlossaryTerm> glossary,
        String strategy,
        List<String> previousIssues
) {
}
