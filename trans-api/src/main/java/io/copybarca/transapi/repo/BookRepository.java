package io.copybarca.transapi.repo;

import io.copybarca.transapi.repo.entity.BookEntity;
import org.springframework.data.jpa.repository.JpaRepository;

public interface BookRepository extends JpaRepository<BookEntity, Long> {
}
