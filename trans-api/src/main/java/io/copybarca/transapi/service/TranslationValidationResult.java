package io.copybarca.transapi.service;

import java.util.List;

public record TranslationValidationResult(
        boolean valid,
        String translation,
        List<String> issues
) {
}
