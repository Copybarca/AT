package io.copybarca.transapi.service;

public class ExtractionCountMismatchException extends RuntimeException {

    public ExtractionCountMismatchException(
            long actualSegments,
            long actualImages,
            long actualRegions
    ) {
        super(
                "Extraction counts do not match stored data: segments=%d, images=%d, regions=%d"
                        .formatted(actualSegments, actualImages, actualRegions)
        );
    }
}
