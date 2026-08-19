package io.copybarca.transapi.repo;

import io.copybarca.transapi.model.InsertionTextRegion;
import java.util.Optional;
import org.springframework.data.jpa.repository.JpaRepository;
import org.springframework.data.jpa.repository.Query;
import org.springframework.data.repository.query.Param;

public interface InsertionTextRegionRepository
        extends JpaRepository<InsertionTextRegion, Long> {

    Optional<InsertionTextRegion> findByStableKey(String stableKey);

    @Query(
            value = """
                    SELECT count(*)
                    FROM trans.insertion_text_region region
                    JOIN trans.segment segment
                      ON segment.insertion_id = region.insertion_id
                    WHERE segment.book_id = :bookId
                    """,
            nativeQuery = true
    )
    long countByBookId(@Param("bookId") Long bookId);
}
