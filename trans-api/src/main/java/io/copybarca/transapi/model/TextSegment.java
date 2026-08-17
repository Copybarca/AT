package io.copybarca.transapi.model;

import jakarta.persistence.Column;
import jakarta.persistence.Entity;
import jakarta.persistence.Id;
import jakarta.persistence.Table;

@Entity
@Table(name = "text_segment", schema = "trans")
public class TextSegment {

    @Id
    @Column(name = "text_hash", nullable = false, columnDefinition = "text")
    private String textHash;

    @Column(nullable = false, columnDefinition = "text")
    private String text;

    protected TextSegment() {
    }

    public TextSegment(String textHash, String text) {
        this.textHash = textHash;
        this.text = text;
    }

    public String getTextHash() {
        return textHash;
    }

    public String getText() {
        return text;
    }

    public void setText(String text) {
        this.text = text;
    }
}
