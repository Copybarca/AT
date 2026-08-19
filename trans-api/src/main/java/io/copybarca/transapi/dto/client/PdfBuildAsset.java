package io.copybarca.transapi.dto.client;

public record PdfBuildAsset(
        String assetKey,
        String mediaType,
        byte[] content
) {
}
