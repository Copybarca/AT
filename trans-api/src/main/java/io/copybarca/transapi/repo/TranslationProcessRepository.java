package io.copybarca.transapi.repo;

import io.copybarca.transapi.model.TranslationProcess;
import java.util.Optional;
import org.springframework.data.jpa.repository.JpaRepository;

public interface TranslationProcessRepository
        extends JpaRepository<TranslationProcess, Long> {

    Optional<TranslationProcess> findByBookIdAndTargetLanguage(
            Long bookId,
            String targetLanguage
    );
}
