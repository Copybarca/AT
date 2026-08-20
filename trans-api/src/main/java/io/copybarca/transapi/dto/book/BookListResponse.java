package io.copybarca.transapi.dto.book;

import java.util.List;

public record BookListResponse(
        List<BookViewResponse> items,
        BookCountersResponse counters
) {
}
