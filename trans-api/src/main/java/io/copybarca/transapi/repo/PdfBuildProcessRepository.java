package io.copybarca.transapi.repo;

import io.copybarca.transapi.model.PdfBuildProcess;
import java.util.Optional;
import org.springframework.data.jpa.repository.JpaRepository;

public interface PdfBuildProcessRepository extends JpaRepository<PdfBuildProcess, Long> {

    Optional<PdfBuildProcess> findByBookIdAndTargetLanguage(
            Long bookId,
            String targetLanguage
    );
}
