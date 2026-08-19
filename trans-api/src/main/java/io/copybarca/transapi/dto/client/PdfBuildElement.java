package io.copybarca.transapi.dto.client;

public record PdfBuildElement(
        int sequentialNumber,
        String type,
        String text,
        String style,
        String assetKey,
        String mediaType,
        String altText
) {

    public static PdfBuildElement text(
            int sequentialNumber,
            String text,
            String style
    ) {
        return new PdfBuildElement(
                sequentialNumber,
                "TEXT",
                text,
                style,
                null,
                null,
                null
        );
    }

    public static PdfBuildElement image(
            int sequentialNumber,
            String assetKey,
            String mediaType
    ) {
        return new PdfBuildElement(
                sequentialNumber,
                "IMAGE",
                null,
                null,
                assetKey,
                mediaType,
                assetKey
        );
    }
}
