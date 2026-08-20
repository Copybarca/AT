package io.copybarca.transapi.dto.book;

public record BookCountersResponse(int all, int progress, int done, int failed) {
}
