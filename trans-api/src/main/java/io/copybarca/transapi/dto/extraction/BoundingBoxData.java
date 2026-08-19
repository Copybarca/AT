package io.copybarca.transapi.dto.extraction;

public record BoundingBoxData(double x0, double y0, double x1, double y1) {

    public String toJson() {
        return "[%s,%s,%s,%s]".formatted(x0, y0, x1, y1);
    }
}
