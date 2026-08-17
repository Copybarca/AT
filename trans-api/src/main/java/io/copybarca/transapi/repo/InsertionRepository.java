package io.copybarca.transapi.repo;

import io.copybarca.transapi.model.Insertion;
import org.springframework.data.jpa.repository.JpaRepository;

public interface InsertionRepository extends JpaRepository<Insertion, Long> {
}
