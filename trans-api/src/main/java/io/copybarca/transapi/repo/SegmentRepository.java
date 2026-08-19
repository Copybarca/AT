package io.copybarca.transapi.repo;

import io.copybarca.transapi.model.Segment;
import org.springframework.data.jpa.repository.JpaRepository;
import java.util.Optional;
import org.springframework.data.jpa.repository.Query;
import org.springframework.data.repository.query.Param;

public interface SegmentRepository extends JpaRepository<Segment, Long> {
    Optional<Segment> findByBookIdAndStableKey(Long bookId, String stableKey);


    @Query(
            value = """
                    SELECT count(*) AS "totalFragments",
                           count(translated.original_text_hash) AS "translatedFragments"
                    FROM trans.segment segment
                    LEFT JOIN trans.translated_segment translated
                      ON translated.original_text_hash = segment.text_segment_hash
                     AND translated.language = :targetLanguage
                    WHERE segment.book_id = :bookId
                      AND segment.text_segment_hash IS NOT NULL
                      AND segment.translatable = true
                    """,
            nativeQuery = true
    )
    TranslationProgress translationProgress(
            @Param("bookId") Long bookId,
            @Param("targetLanguage") String targetLanguage
    );
    @Query(
            value = """
                    SELECT count(*)
                    FROM trans.segment
                    WHERE book_id = :bookId
                      AND text_segment_hash IS NOT NULL
                    """,
            nativeQuery = true
    )
    long countTextPositions(@Param("bookId") Long bookId);

    @Query(
            value = """
                    SELECT count(*)
                    FROM trans.segment
                    WHERE book_id = :bookId
                      AND insertion_id IS NOT NULL
                    """,
            nativeQuery = true
    )
    long countImagePositions(@Param("bookId") Long bookId);

}
