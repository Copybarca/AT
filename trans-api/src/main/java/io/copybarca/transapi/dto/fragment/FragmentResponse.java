package io.copybarca.transapi.dto.fragment;

public record FragmentResponse(
        Long id,
        Long bookId,
        int sequence,
        String originalText,
        String translatedText,
        int version
) {
}
