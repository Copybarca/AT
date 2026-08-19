package io.copybarca.transapi.repo;

import io.copybarca.transapi.model.PdfBuildProcess;
import io.copybarca.transapi.model.ProcessStatus;
import java.util.List;
import java.util.Optional;
import org.springframework.data.jpa.repository.JpaRepository;

public interface PdfBuildProcessRepository extends JpaRepository<PdfBuildProcess, Long> {

    Optional<PdfBuildProcess> findByBook_IdAndTargetLanguage(
            Long bookId,
            String targetLanguage
    );

    List<PdfBuildProcess> findByStatus(ProcessStatus status);
}
