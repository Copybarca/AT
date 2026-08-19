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
import jakarta.persistence.ManyToOne;
import jakarta.persistence.Table;
import java.time.Instant;

@Entity
@Table(name = "pdf_build_process", schema = "\"scheduled-processes\"")
public class PdfBuildProcess {

    @Id
    @GeneratedValue(strategy = GenerationType.IDENTITY)
    private Long id;

    @ManyToOne(fetch = FetchType.LAZY, optional = false)
    @JoinColumn(name = "book_id", nullable = false)
    private Book book;

    @Column(name = "target_language", nullable = false, length = 32)
    private String targetLanguage;

    @Enumerated(EnumType.STRING)
    @Column(nullable = false, length = 16)
    private ProcessStatus status = ProcessStatus.IN_PROGRESS;

    @Column(name = "started_at", nullable = false)
    private Instant startedAt = Instant.now();

    @Column(name = "completed_at")
    private Instant completedAt;

    protected PdfBuildProcess() {
    }

    public PdfBuildProcess(Book book, String targetLanguage) {
        this.book = book;
        this.targetLanguage = targetLanguage;
    }

    public Long getId() {
        return id;
    }

    public Long getBookId() {
        return book.getId();
    }

    public String getTargetLanguage() {
        return targetLanguage;
    }

    public ProcessStatus getStatus() {
        return status;
    }

    public void complete() {
        status = ProcessStatus.COMPLETED;
        completedAt = Instant.now();
    }
}
