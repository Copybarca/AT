package io.copybarca.transapi.repo;

import static org.junit.jupiter.api.Assertions.assertEquals;

import io.copybarca.transapi.model.Book;
import io.copybarca.transapi.model.PdfBuildProcess;
import io.copybarca.transapi.model.PdfExtractionProcess;
import io.copybarca.transapi.model.ProcessStatus;
import io.copybarca.transapi.model.TranslationProcess;
import org.junit.jupiter.api.Test;
import org.junit.jupiter.api.condition.EnabledIfEnvironmentVariable;
import org.springframework.beans.factory.annotation.Autowired;
import org.springframework.boot.test.context.SpringBootTest;
import org.springframework.jdbc.core.JdbcTemplate;
import org.springframework.test.context.DynamicPropertyRegistry;
import org.springframework.test.context.DynamicPropertySource;
import org.springframework.transaction.annotation.Transactional;

@SpringBootTest
@Transactional
@EnabledIfEnvironmentVariable(named = "RUN_DB_TESTS", matches = "true")
class PipelineRepositoryIntegrationTest {

    @DynamicPropertySource
    static void configureLocalInfrastructure(DynamicPropertyRegistry registry) {
        registry.add("spring.datasource.url", () -> "jdbc:postgresql://localhost:5434/data");
        registry.add("spring.datasource.username", () -> "data");
        registry.add("spring.datasource.password", () -> "data");
        registry.add("storage.s3.endpoint", () -> "http://localhost:9000");
        registry.add("storage.s3.path-style-access", () -> "true");
        registry.add("storage.s3.access-key", () -> "minioadmin");
        registry.add("storage.s3.secret-key", () -> "minioadmin");
    }

    @Autowired
    private JdbcTemplate jdbc;

    @Autowired
    private BookRepository books;

    @Autowired
    private SegmentRepository segments;

    @Autowired
    private PdfExtractionProcessRepository extractions;

    @Autowired
    private TranslationProcessRepository translations;

    @Autowired
    private PdfBuildProcessRepository builds;

    @Test
    void persistsAllThreeProcessTypesWithTwoStateLifecycle() {
        Book book = books.save(new Book("Book", "eng"));

        PdfExtractionProcess extraction = extractions.save(new PdfExtractionProcess(book));
        TranslationProcess translation = translations.save(
                new TranslationProcess(book, "ru")
        );
        PdfBuildProcess build = builds.save(new PdfBuildProcess(book, "ru"));

        assertEquals(ProcessStatus.IN_PROGRESS, extraction.getStatus());
        assertEquals(ProcessStatus.IN_PROGRESS, translation.getStatus());
        assertEquals(ProcessStatus.IN_PROGRESS, build.getStatus());

        extraction.complete();
        translation.complete();
        build.complete();

        assertEquals(ProcessStatus.COMPLETED, extraction.getStatus());
        assertEquals(ProcessStatus.COMPLETED, translation.getStatus());
        assertEquals(ProcessStatus.COMPLETED, build.getStatus());
    }

    @Test
    void calculatesTranslationProgressFromActualBookPositions() {
        Long bookId = jdbc.queryForObject(
                """
                INSERT INTO trans.book(title, original_language)
                VALUES ('Progress Book', 'eng')
                RETURNING id
                """,
                Long.class
        );
        jdbc.update(
                """
                INSERT INTO trans.text_segment(text_hash, text)
                SELECT 'hash-' || value, 'text-' || value
                FROM generate_series(1, 100) AS value
                """
        );
        jdbc.update(
                """
                INSERT INTO trans.segment(
                    book_id,
                    stable_key,
                    text_segment_hash,
                    sequential_number,
                    physical_page,
                    bbox_json,
                    style,
                    translatable
                )
                SELECT ?, 'P0001-B' || lpad(value::text, 3, '0'),
                       'hash-' || value, value, 1, '[0,0,1,1]', 'BODY', true
                FROM generate_series(1, 100) AS value
                """,
                bookId
        );

        assertProgress(bookId, 100, 0);

        jdbc.update(
                """
                INSERT INTO trans.translated_segment(
                    original_text_hash,
                    language,
                    translation,
                    retries
                )
                SELECT 'hash-' || value, 'ru', 'translation-' || value, 0
                FROM generate_series(1, 73) AS value
                """
        );
        assertProgress(bookId, 100, 73);

        jdbc.update(
                """
                INSERT INTO trans.translated_segment(
                    original_text_hash,
                    language,
                    translation,
                    retries
                )
                SELECT 'hash-' || value, 'ru', 'translation-' || value, 0
                FROM generate_series(74, 100) AS value
                """
        );
        assertProgress(bookId, 100, 100);
    }

    private void assertProgress(Long bookId, long total, long translated) {
        TranslationProgress progress = segments.translationProgress(bookId, "ru");

        assertEquals(total, progress.getTotalFragments());
        assertEquals(translated, progress.getTranslatedFragments());
    }
}
