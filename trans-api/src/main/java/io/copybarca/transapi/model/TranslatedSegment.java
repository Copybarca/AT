package io.copybarca.transapi.model;

import jakarta.persistence.Column;
import jakarta.persistence.EmbeddedId;
import jakarta.persistence.Entity;
import jakarta.persistence.FetchType;
import jakarta.persistence.ForeignKey;
import jakarta.persistence.Index;
import jakarta.persistence.JoinColumn;
import jakarta.persistence.ManyToOne;
import jakarta.persistence.MapsId;
import jakarta.persistence.Table;

@Entity
@Table(
        name = "translated_segment",
        schema = "trans",
        indexes = @Index(name = "idx_translated_segment_language", columnList = "language")
)
public class TranslatedSegment {

    @EmbeddedId
    private TranslatedSegmentId id;

    @MapsId("originalTextHash")
    @ManyToOne(fetch = FetchType.LAZY, optional = false)
    @JoinColumn(
            name = "original_text_hash",
            referencedColumnName = "text_hash",
            nullable = false,
            columnDefinition = "text",
            foreignKey = @ForeignKey(name = "fk_translated_segment_original_text")
    )
    private TextSegment originalTextSegment;

    @Column(nullable = false, columnDefinition = "text")
    private String translation;

    @Column
    private Short evaluation;

    @Column(nullable = false)
    private Integer retries = 0;

    protected TranslatedSegment() {
    }

    public TranslatedSegment(
            TextSegment originalTextSegment,
            String language,
            String translation
    ) {
        this.originalTextSegment = originalTextSegment;
        this.id = new TranslatedSegmentId(originalTextSegment.getTextHash(), language);
        this.translation = translation;
    }

    public TranslatedSegmentId getId() {
        return id;
    }

    public TextSegment getOriginalTextSegment() {
        return originalTextSegment;
    }

    public String getTranslation() {
        return translation;
    }

    public void setTranslation(String translation) {
        this.translation = translation;
    }

    public Short getEvaluation() {
        return evaluation;
    }

    public void setEvaluation(Short evaluation) {
        this.evaluation = evaluation;
    }

    public Integer getRetries() {
        return retries;
    }

    public void setRetries(Integer retries) {
        this.retries = retries;
    }
}
