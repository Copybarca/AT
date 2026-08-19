package io.copybarca.transapi.model;

import jakarta.persistence.Column;
import jakarta.persistence.Entity;
import jakarta.persistence.GeneratedValue;
import jakarta.persistence.GenerationType;
import jakarta.persistence.Id;
import jakarta.persistence.Table;
import jakarta.persistence.UniqueConstraint;

@Entity
@Table(
        name = "insertion",
        schema = "trans",
        uniqueConstraints = @UniqueConstraint(name = "insertion_path_key", columnNames = "path")
)
public class Insertion {

    @Id
    @GeneratedValue(strategy = GenerationType.IDENTITY)
    private Long id;

    @Column(nullable = false, columnDefinition = "text")
    private String path;

    @Column(name = "media_type", length = 64)
    private String mediaType;

    @Column(length = 80)
    private String checksum;

    protected Insertion() {
    }

    public Insertion(String path) {
        this.path = path;
    }

    public Insertion(String path, String mediaType, String checksum) {
        this.path = path;
        this.mediaType = mediaType;
        this.checksum = checksum;
    }

    public Long getId() {
        return id;
    }

    public String getPath() {
        return path;
    }

    public void setPath(String path) {
        this.path = path;
    }

    public String getMediaType() {
        return mediaType;
    }

    public String getChecksum() {
        return checksum;
    }
}
