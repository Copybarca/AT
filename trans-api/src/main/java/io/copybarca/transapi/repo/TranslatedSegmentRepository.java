package io.copybarca.transapi.repo;

import io.copybarca.transapi.model.TranslatedSegment;
import io.copybarca.transapi.model.TranslatedSegmentId;
import org.springframework.data.jpa.repository.JpaRepository;

public interface TranslatedSegmentRepository
        extends JpaRepository<TranslatedSegment, TranslatedSegmentId> {
}
