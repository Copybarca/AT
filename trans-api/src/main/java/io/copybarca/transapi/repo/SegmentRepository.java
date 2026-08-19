package io.copybarca.transapi.repo;

import io.copybarca.transapi.model.Segment;
import org.springframework.data.jpa.repository.JpaRepository;
import org.springframework.data.jpa.repository.Query;
import org.springframework.data.repository.query.Param;

public interface SegmentRepository extends JpaRepository<Segment, Long> {

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
}
