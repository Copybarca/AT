package io.copybarca.transapi.repo;

public interface TranslatablePosition {

    Long getSegmentId();

    String getStableKey();

    String getSourceHash();

    String getSourceText();

    String getSourceLanguage();
}
