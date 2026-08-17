package io.copybarca.transapi.model;

import jakarta.persistence.Column;
import jakarta.persistence.Entity;
import jakarta.persistence.GeneratedValue;
import jakarta.persistence.GenerationType;
import jakarta.persistence.Id;
import jakarta.persistence.Table;

@Entity
@Table(name = "book", schema = "trans")
public class Book {

    @Id
    @GeneratedValue(strategy = GenerationType.IDENTITY)
    private Long id;

    @Column(nullable = false, length = 128)
    private String title;

    @Column(name = "original_language", nullable = false, length = 3)
    private String originalLanguage;

    @Column
    private String path;

    @Column(name = "translated_path")
    private String translatedPath;

    protected Book() {
    }

    public Book(String title, String originalLanguage) {
        this.title = title;
        this.originalLanguage = originalLanguage;
    }

    public Long getId() {
        return id;
    }

    public void setId(Long id) {
        this.id = id;
    }

    public String getTitle() {
        return title;
    }

    public void setTitle(String title) {
        this.title = title;
    }

    public String getOriginalLanguage() {
        return originalLanguage;
    }

    public void setOriginalLanguage(String originalLanguage) {
        this.originalLanguage = originalLanguage;
    }

    public String getPath() {
        return path;
    }

    public void setPath(String path) {
        this.path = path;
    }

    public String getTranslatedPath() {
        return translatedPath;
    }

    public void setTranslatedPath(String translatedPath) {
        this.translatedPath = translatedPath;
    }
}
