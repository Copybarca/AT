package io.copybarca.transapi.repo;

import io.copybarca.transapi.model.PdfExtractionProcess;
import io.copybarca.transapi.model.ProcessStatus;
import java.util.List;
import java.util.Optional;
import org.springframework.data.jpa.repository.JpaRepository;

public interface PdfExtractionProcessRepository
        extends JpaRepository<PdfExtractionProcess, Long> {

    Optional<PdfExtractionProcess> findByBookId(Long bookId);

    List<PdfExtractionProcess> findByStatus(ProcessStatus status);
}
