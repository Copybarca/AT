package io.copybarca.transapi.service;

import java.util.ArrayList;
import java.util.LinkedHashSet;
import java.util.List;
import java.util.Locale;
import java.util.Set;
import java.util.regex.Matcher;
import java.util.regex.Pattern;
import org.springframework.stereotype.Component;

@Component
public class TranslationResponseValidator {

    private static final Pattern REQUIRED_LITERAL = Pattern.compile(
            "https?://\\S+|RFC\\s+\\d+|"
                    + "(?:\\d{1,3}\\.){3}\\d{1,3}(?::\\d+)?|"
                    + "\\d+(?:[.-]\\d+)+|\\d+"
    );
    private static final Pattern PROTECTED_TOKEN = Pattern.compile(
            "\\bZXQ[A-Z]+\\b"
    );

    public TranslationValidationResult validate(
            String stableKey,
            String source,
            String rawResponse
    ) {
        List<String> issues = new ArrayList<>();
        String marker = "<<<" + stableKey + ">>>";
        int markerCount = count(rawResponse, marker);
        if (markerCount == 0) {
            issues.add("EXPECTED_MARKER_MISSING");
        } else if (markerCount != 1) {
            issues.add("EXPECTED_MARKER_COUNT");
        }

        String translation = markerCount > 0
                ? rawResponse.substring(rawResponse.indexOf(marker) + marker.length()).trim()
                : rawResponse.trim();
        if (translation.isEmpty()) {
            issues.add("EMPTY_TRANSLATION");
        }

        for (String literal : requiredLiterals(source)) {
            if (!translation.contains(literal)) {
                issues.add("REQUIRED_LITERAL_MISSING:" + literal);
            }
        }
        if (PROTECTED_TOKEN.matcher(translation).find()) {
            issues.add("PROTECTED_TOKEN_REMAINS");
        }

        String lowered = translation.toLowerCase(Locale.ROOT);
        if (lowered.contains("alternative translation:")
                || lowered.contains("here is the translation:")
                || lowered.contains("translation options:")) {
            issues.add("MODEL_COMMENTARY");
        }
        return new TranslationValidationResult(
                issues.isEmpty(),
                translation,
                List.copyOf(issues)
        );
    }

    private static Set<String> requiredLiterals(String source) {
        Set<String> literals = new LinkedHashSet<>();
        Matcher matcher = REQUIRED_LITERAL.matcher(source);
        while (matcher.find()) {
            String value = matcher.group();
            while (value.endsWith(".") || value.endsWith(",")) {
                value = value.substring(0, value.length() - 1);
            }
            literals.add(value);
        }
        return literals;
    }

    private static int count(String value, String needle) {
        int count = 0;
        int offset = 0;
        while ((offset = value.indexOf(needle, offset)) >= 0) {
            count++;
            offset += needle.length();
        }
        return count;
    }
}
