package io.copybarca.transapi.model;

import jakarta.persistence.Column;
import jakarta.persistence.Entity;
import jakarta.persistence.FetchType;
import jakarta.persistence.ForeignKey;
import jakarta.persistence.GeneratedValue;
import jakarta.persistence.GenerationType;
import jakarta.persistence.Id;
import jakarta.persistence.Index;
import jakarta.persistence.JoinColumn;
import jakarta.persistence.ManyToOne;
import jakarta.persistence.Table;
import jakarta.persistence.UniqueConstraint;

@Entity
@Table(
        name = "segment",
        schema = "trans",
        uniqueConstraints = {
                @UniqueConstraint(
                        name = "uq_segment_book_sequence",
                        columnNames = {"book_id", "sequential_number"}
                ),
                @UniqueConstraint(
                        name = "uq_segment_book_stable_key",
                        columnNames = {"book_id", "stable_key"}
                )
        },
        indexes = {
                @Index(name = "idx_segment_insertion_id", columnList = "insertion_id"),
                @Index(name = "idx_segment_text_segment_hash", columnList = "text_segment_hash")
        }
)
public class Segment {

    @Id
    @GeneratedValue(strategy = GenerationType.IDENTITY)
    private Long id;

    @ManyToOne(fetch = FetchType.LAZY, optional = false)
    @JoinColumn(
            name = "book_id",
            nullable = false,
            foreignKey = @ForeignKey(name = "fk_segment_book")
    )
    private Book book;

    @Column(name = "stable_key", nullable = false, length = 64)
    private String stableKey;

    @ManyToOne(fetch = FetchType.LAZY)
    @JoinColumn(
            name = "insertion_id",
            foreignKey = @ForeignKey(name = "fk_segment_insertion")
    )
    private Insertion insertion;

    @ManyToOne(fetch = FetchType.LAZY)
    @JoinColumn(
            name = "text_segment_hash",
            referencedColumnName = "text_hash",
            columnDefinition = "text",
            foreignKey = @ForeignKey(name = "fk_segment_text_segment")
    )
    private TextSegment textSegment;

    @Column(name = "sequential_number", nullable = false)
    private Integer sequentialNumber;

    @Column(name = "physical_page")
    private Integer physicalPage;

    @Column(name = "bbox_json", columnDefinition = "text")
    private String bboxJson;

    @Column(length = 32)
    private String style;

    @Column(nullable = false)
    private Boolean translatable = true;

    protected Segment() {
    }

    public Segment(Book book, String stableKey, Integer sequentialNumber) {
        this.book = book;
        this.stableKey = stableKey;
        this.sequentialNumber = sequentialNumber;
    }

    public Long getId() {
        return id;
    }

    public Book getBook() {
        return book;
    }

    public void setBook(Book book) {
        this.book = book;
    }

    public String getStableKey() {
        return stableKey;
    }

    public void setStableKey(String stableKey) {
        this.stableKey = stableKey;
    }

    public Insertion getInsertion() {
        return insertion;
    }

    public void setInsertion(Insertion insertion) {
        this.insertion = insertion;
    }

    public TextSegment getTextSegment() {
        return textSegment;
    }

    public void setTextSegment(TextSegment textSegment) {
        this.textSegment = textSegment;
    }

    public Integer getSequentialNumber() {
        return sequentialNumber;
    }

    public void setSequentialNumber(Integer sequentialNumber) {
        this.sequentialNumber = sequentialNumber;
    }

    public void applyTextExtraction(
            TextSegment textSegment,
            Integer sequentialNumber,
            Integer physicalPage,
            String bboxJson,
            String style,
            boolean translatable
    ) {
        this.textSegment = textSegment;
        this.insertion = null;
        this.sequentialNumber = sequentialNumber;
        this.physicalPage = physicalPage;
        this.bboxJson = bboxJson;
        this.style = style;
        this.translatable = translatable;
    }

    public void applyImageExtraction(
            Insertion insertion,
            Integer sequentialNumber,
            Integer physicalPage,
            String bboxJson
    ) {
        this.insertion = insertion;
        this.textSegment = null;
        this.sequentialNumber = sequentialNumber;
        this.physicalPage = physicalPage;
        this.bboxJson = bboxJson;
        this.style = null;
        this.translatable = false;
    }

}
