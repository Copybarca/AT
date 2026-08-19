package io.copybarca.transapi.repo;

import io.copybarca.transapi.model.ProcessStatus;
import io.copybarca.transapi.model.TranslationProcess;
import java.util.List;
import java.util.Optional;
import org.springframework.data.jpa.repository.JpaRepository;

public interface TranslationProcessRepository
        extends JpaRepository<TranslationProcess, Long> {

    Optional<TranslationProcess> findByBook_IdAndTargetLanguage(
            Long bookId,
            String targetLanguage
    );

    List<TranslationProcess> findByBook_IdAndStatus(
            Long bookId,
            ProcessStatus status
    );

    List<TranslationProcess> findByStatus(ProcessStatus status);
}
