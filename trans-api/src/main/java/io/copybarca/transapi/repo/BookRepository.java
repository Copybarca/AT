package io.copybarca.transapi.repo;

import io.copybarca.transapi.model.Book;
import org.springframework.data.jpa.repository.JpaRepository;

public interface BookRepository extends JpaRepository<Book, Long> {
}
