package io.copybarca.transapi.repo;

import io.copybarca.transapi.model.Segment;
import org.springframework.data.jpa.repository.JpaRepository;

public interface SegmentRepository extends JpaRepository<Segment, Long> {
}
