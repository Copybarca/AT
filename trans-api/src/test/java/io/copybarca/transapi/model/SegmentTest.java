package io.copybarca.transapi.model;

import static org.junit.jupiter.api.Assertions.assertEquals;
import static org.junit.jupiter.api.Assertions.assertFalse;
import static org.junit.jupiter.api.Assertions.assertTrue;

import jakarta.persistence.Column;
import jakarta.persistence.Table;
import java.util.Arrays;
import java.util.Set;
import org.junit.jupiter.api.Test;

class SegmentTest {

    @Test
    void keepsStableKeyRequiredForPersistence() {
        Book book = new Book("Book", "eng");

        Segment segment = new Segment(book, "P0001-B000", 1);

        assertEquals("P0001-B000", segment.getStableKey());
        assertEquals(1, segment.getSequentialNumber());
    }

    @Test
    void mapsStableKeyToTheDatabaseContract() throws NoSuchFieldException {
        Column column = Segment.class.getDeclaredField("stableKey").getAnnotation(Column.class);

        assertEquals("stable_key", column.name());
        assertFalse(column.nullable());
        assertEquals(64, column.length());

        Table table = Segment.class.getAnnotation(Table.class);
        assertTrue(Arrays.stream(table.uniqueConstraints()).anyMatch(constraint ->
                constraint.name().equals("uq_segment_book_stable_key")
                        && Set.of(constraint.columnNames()).equals(Set.of("book_id", "stable_key"))
        ));
    }
}
