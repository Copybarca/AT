package io.copybarca.transapi.model;

import jakarta.persistence.Column;
import jakarta.persistence.Embeddable;
import java.io.Serial;
import java.io.Serializable;
import java.util.Objects;

@Embeddable
public class TranslatedSegmentId implements Serializable {

    @Serial
    private static final long serialVersionUID = 1L;

    @Column(name = "original_text_hash", nullable = false, columnDefinition = "text")
    private String originalTextHash;

    @Column(nullable = false, length = 32)
    private String language;

    protected TranslatedSegmentId() {
    }

    public TranslatedSegmentId(String originalTextHash, String language) {
        this.originalTextHash = originalTextHash;
        this.language = language;
    }

    public String getOriginalTextHash() {
        return originalTextHash;
    }

    public String getLanguage() {
        return language;
    }

    @Override
    public boolean equals(Object object) {
        if (this == object) {
            return true;
        }
        if (!(object instanceof TranslatedSegmentId that)) {
            return false;
        }
        return Objects.equals(originalTextHash, that.originalTextHash)
                && Objects.equals(language, that.language);
    }

    @Override
    public int hashCode() {
        return Objects.hash(originalTextHash, language);
    }
}
