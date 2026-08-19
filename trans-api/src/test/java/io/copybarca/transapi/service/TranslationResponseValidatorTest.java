package io.copybarca.transapi.service;

import static org.junit.jupiter.api.Assertions.assertEquals;
import static org.junit.jupiter.api.Assertions.assertFalse;
import static org.junit.jupiter.api.Assertions.assertTrue;

import org.junit.jupiter.api.Test;

class TranslationResponseValidatorTest {

    private final TranslationResponseValidator validator =
            new TranslationResponseValidator();

    @Test
    void acceptsOneMarkedTranslationThatPreservesRequiredLiterals() {
        TranslationValidationResult result = validator.validate(
                "P0001-B001",
                "OAuth 2.0 uses RFC 7523 at http://127.0.0.1:3000.",
                "<<<P0001-B001>>>\nOAuth 2.0 использует RFC 7523 по адресу "
                        + "http://127.0.0.1:3000."
        );

        assertTrue(result.valid());
        assertEquals(
                "OAuth 2.0 использует RFC 7523 по адресу http://127.0.0.1:3000.",
                result.translation()
        );
        assertTrue(result.issues().isEmpty());
    }

    @Test
    void rejectsMissingMarkerAndLostNumericLiteral() {
        TranslationValidationResult result = validator.validate(
                "P0001-B001",
                "Version 2.6 covers pages 251-254.",
                "Версия охватывает страницы 251-254."
        );

        assertFalse(result.valid());
        assertTrue(result.issues().contains("EXPECTED_MARKER_MISSING"));
        assertTrue(result.issues().contains("REQUIRED_LITERAL_MISSING:2.6"));
    }

    @Test
    void rejectsMultipleMarkersAndModelCommentary() {
        TranslationValidationResult result = validator.validate(
                "P0001-B001",
                "Source.",
                "<<<P0001-B001>>>\nПеревод.\n<<<P0001-B001>>>\n"
                        + "Alternative translation:"
        );

        assertFalse(result.valid());
        assertTrue(result.issues().contains("EXPECTED_MARKER_COUNT"));
        assertTrue(result.issues().contains("MODEL_COMMENTARY"));
    }
}
