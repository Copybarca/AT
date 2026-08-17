package io.copybarca.transapi.repo;

import io.copybarca.transapi.model.TextSegment;
import org.springframework.data.jpa.repository.JpaRepository;

public interface TextSegmentRepository extends JpaRepository<TextSegment, String> {
}
