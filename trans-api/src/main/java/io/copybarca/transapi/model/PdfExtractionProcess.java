package io.copybarca.transapi.model;

import jakarta.persistence.Column;
import jakarta.persistence.Entity;
import jakarta.persistence.EnumType;
import jakarta.persistence.Enumerated;
import jakarta.persistence.FetchType;
import jakarta.persistence.GeneratedValue;
import jakarta.persistence.GenerationType;
import jakarta.persistence.Id;
import jakarta.persistence.JoinColumn;
import jakarta.persistence.OneToOne;
import jakarta.persistence.Table;
import java.time.Instant;

@Entity
@Table(name = "pdf_extraction_process", schema = "\"scheduled-processes\"")
public class PdfExtractionProcess {

    @Id
    @GeneratedValue(strategy = GenerationType.IDENTITY)
    private Long id;

    @OneToOne(fetch = FetchType.LAZY, optional = false)
    @JoinColumn(name = "book_id", nullable = false, unique = true)
    private Book book;

    @Enumerated(EnumType.STRING)
    @Column(nullable = false, length = 16)
    private ProcessStatus status = ProcessStatus.IN_PROGRESS;

    @Column(name = "pdf_sha256", length = 80)
    private String pdfSha256;

    @Column(name = "extractor_version", length = 64)
    private String extractorVersion;

    @Column(name = "expected_segment_count")
    private Integer expectedSegmentCount;

    @Column(name = "expected_image_count")
    private Integer expectedImageCount;

    @Column(name = "expected_region_count")
    private Integer expectedRegionCount;

    @Column(name = "started_at", nullable = false)
    private Instant startedAt = Instant.now();

    @Column(name = "completed_at")
    private Instant completedAt;

    protected PdfExtractionProcess() {
    }

    public PdfExtractionProcess(Book book) {
        this.book = book;
    }

    public Long getId() {
        return id;
    }

    public Long getBookId() {
        return book.getId();
    }

    public ProcessStatus getStatus() {
        return status;
    }

    public void recordManifest(
            String pdfSha256,
            String extractorVersion,
            int segmentCount,
            int imageCount,
            int regionCount
    ) {
        this.pdfSha256 = pdfSha256;
        this.extractorVersion = extractorVersion;
        this.expectedSegmentCount = segmentCount;
        this.expectedImageCount = imageCount;
        this.expectedRegionCount = regionCount;
    }

    public void complete() {
        status = ProcessStatus.COMPLETED;
        completedAt = Instant.now();
    }

    public void fail() {
        status = ProcessStatus.FAILED;
        completedAt = Instant.now();
    }

    public void restart() {
        status = ProcessStatus.IN_PROGRESS;
        startedAt = Instant.now();
        completedAt = null;
    }
}
