package io.copybarca.transapi.model;

import jakarta.persistence.Column;
import jakarta.persistence.Entity;
import jakarta.persistence.FetchType;
import jakarta.persistence.GeneratedValue;
import jakarta.persistence.GenerationType;
import jakarta.persistence.Id;
import jakarta.persistence.JoinColumn;
import jakarta.persistence.ManyToOne;
import jakarta.persistence.Table;
import java.math.BigDecimal;

@Entity
@Table(name = "insertion_text_region", schema = "trans")
public class InsertionTextRegion {

    @Id
    @GeneratedValue(strategy = GenerationType.IDENTITY)
    private Long id;

    @ManyToOne(fetch = FetchType.LAZY, optional = false)
    @JoinColumn(name = "insertion_id", nullable = false)
    private Insertion insertion;

    @Column(name = "stable_key", nullable = false, length = 64, unique = true)
    private String stableKey;

    @ManyToOne(fetch = FetchType.LAZY, optional = false)
    @JoinColumn(
            name = "original_text_hash",
            referencedColumnName = "text_hash",
            nullable = false
    )
    private TextSegment originalText;

    @Column(name = "sequential_number", nullable = false)
    private Integer sequentialNumber;

    @Column(name = "pixel_bbox_json", nullable = false, columnDefinition = "text")
    private String pixelBboxJson;

    @Column(name = "ocr_confidence", precision = 5, scale = 2)
    private BigDecimal ocrConfidence;

    protected InsertionTextRegion() {
    }

    public InsertionTextRegion(
            Insertion insertion,
            String stableKey,
            TextSegment originalText,
            Integer sequentialNumber,
            String pixelBboxJson,
            BigDecimal ocrConfidence
    ) {
        this.insertion = insertion;
        this.stableKey = stableKey;
        this.originalText = originalText;
        this.sequentialNumber = sequentialNumber;
        this.pixelBboxJson = pixelBboxJson;
        this.ocrConfidence = ocrConfidence;
    }

    public Long getId() {
        return id;
    }

    public String getStableKey() {
        return stableKey;
    }
}
