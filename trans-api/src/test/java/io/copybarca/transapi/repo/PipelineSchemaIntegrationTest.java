package io.copybarca.transapi.repo;

import static org.junit.jupiter.api.Assertions.assertEquals;
import static org.junit.jupiter.api.Assertions.assertTrue;

import java.util.List;
import org.junit.jupiter.api.Test;
import org.junit.jupiter.api.condition.EnabledIfEnvironmentVariable;
import org.springframework.beans.factory.annotation.Autowired;
import org.springframework.boot.test.context.SpringBootTest;
import org.springframework.jdbc.core.JdbcTemplate;
import org.springframework.test.context.DynamicPropertyRegistry;
import org.springframework.test.context.DynamicPropertySource;

@SpringBootTest
@EnabledIfEnvironmentVariable(named = "RUN_DB_TESTS", matches = "true")
class PipelineSchemaIntegrationTest {

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

    @Test
    void createsQuotedProcessSchemaAndAllThreeProcessTables() {
        List<String> tables = jdbc.queryForList(
                """
                SELECT table_name
                FROM information_schema.tables
                WHERE table_schema = 'scheduled-processes'
                ORDER BY table_name
                """,
                String.class
        );

        assertEquals(
                List.of(
                        "pdf_build_process",
                        "pdf_extraction_process",
                        "translation_process"
                ),
                tables
        );
    }

    @Test
    void addsExtractionMetadataNeededByWorkerContracts() {
        List<String> columns = jdbc.queryForList(
                """
                SELECT column_name
                FROM information_schema.columns
                WHERE table_schema = 'trans'
                  AND table_name = 'segment'
                  AND column_name IN (
                    'bbox_json',
                    'physical_page',
                    'style',
                    'translatable'
                  )
                ORDER BY column_name
                """,
                String.class
        );

        assertEquals(
                List.of("bbox_json", "physical_page", "style", "translatable"),
                columns
        );

        Integer regionTable = jdbc.queryForObject(
                """
                SELECT count(*)
                FROM information_schema.tables
                WHERE table_schema = 'trans'
                  AND table_name = 'insertion_text_region'
                """,
                Integer.class
        );
        assertEquals(1, regionTable);
    }

    @Test
    void processStatusChecksAllowOnlyInProgressAndCompleted() {
        List<String> definitions = jdbc.queryForList(
                """
                SELECT pg_get_constraintdef(c.oid)
                FROM pg_constraint c
                JOIN pg_namespace n ON n.oid = c.connamespace
                WHERE n.nspname = 'scheduled-processes'
                  AND c.contype = 'c'
                """,
                String.class
        );

        assertEquals(3, definitions.size());
        assertTrue(definitions.stream().allMatch(definition ->
                definition.contains("IN_PROGRESS")
                        && definition.contains("COMPLETED")
        ));
    }
}
