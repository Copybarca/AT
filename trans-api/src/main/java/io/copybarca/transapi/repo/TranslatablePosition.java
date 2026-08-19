package io.copybarca.transapi.repo;

public interface TranslatablePosition {

    String getStableKey();

    String getSourceHash();

    String getSourceText();

    String getSourceLanguage();
}
