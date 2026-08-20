package io.copybarca.transapi.controller;

import static org.mockito.ArgumentMatchers.any;
import static org.mockito.Mockito.verify;
import static org.mockito.Mockito.when;
import static org.springframework.test.web.servlet.request.MockMvcRequestBuilders.get;
import static org.springframework.test.web.servlet.request.MockMvcRequestBuilders.multipart;
import static org.springframework.test.web.servlet.request.MockMvcRequestBuilders.put;
import static org.springframework.test.web.servlet.result.MockMvcResultMatchers.jsonPath;
import static org.springframework.test.web.servlet.result.MockMvcResultMatchers.status;

import io.copybarca.transapi.dto.book.BookCountersResponse;
import io.copybarca.transapi.dto.book.BookListResponse;
import io.copybarca.transapi.dto.book.BookResponse;
import io.copybarca.transapi.dto.fragment.FragmentResponse;
import io.copybarca.transapi.repo.BookRepository;
import io.copybarca.transapi.service.BookFileStorage;
import io.copybarca.transapi.service.BookQueryService;
import io.copybarca.transapi.service.BookService;
import io.copybarca.transapi.service.FragmentService;
import io.copybarca.transapi.service.PublicBuildService;
import java.util.List;
import org.junit.jupiter.api.BeforeEach;
import org.junit.jupiter.api.Test;
import org.junit.jupiter.api.extension.ExtendWith;
import org.mockito.Mock;
import org.mockito.junit.jupiter.MockitoExtension;
import org.springframework.http.MediaType;
import org.springframework.mock.web.MockMultipartFile;
import org.springframework.test.web.servlet.MockMvc;
import org.springframework.test.web.servlet.setup.MockMvcBuilders;

@ExtendWith(MockitoExtension.class)
class PublicApiContractTest {

    @Mock BookService books;
    @Mock BookQueryService query;
    @Mock PublicBuildService builds;
    @Mock BookRepository repository;
    @Mock BookFileStorage storage;
    @Mock FragmentService fragments;

    private MockMvc mvc;

    @BeforeEach
    void setUp() {
        mvc = MockMvcBuilders.standaloneSetup(
                new BookController(books, query, builds, repository, storage),
                new FragmentController(fragments)
        ).setControllerAdvice(new ApiExceptionHandler()).build();
    }

    @Test
    void listsBooksUsingFrontendShape() throws Exception {
        when(query.list("", "all")).thenReturn(
                new BookListResponse(
                        List.of(),
                        new BookCountersResponse(0, 0, 0, 0)
                )
        );

        mvc.perform(get("/api/v1/books"))
                .andExpect(status().isOk())
                .andExpect(jsonPath("$.items").isArray())
                .andExpect(jsonPath("$.counters.all").value(0));
    }

    @Test
    void uploadsUsingOriginalLanguageField() throws Exception {
        var pdf = new MockMultipartFile(
                "file",
                "two-pages.pdf",
                MediaType.APPLICATION_PDF_VALUE,
                "%PDF-1.7\n".getBytes()
        );
        when(books.createBook(any(), any(), any()))
                .thenReturn(new BookResponse(7L, "Two pages", "eng", "s3://original", null, null));

        mvc.perform(multipart("/api/v1/books")
                        .file(pdf)
                        .param("title", "Two pages")
                        .param("originalLanguage", "eng"))
                .andExpect(status().isCreated())
                .andExpect(jsonPath("$.id").value(7));

        verify(books).createBook(any(), any(), org.mockito.ArgumentMatchers.eq("eng"));
    }

    @Test
    void savesManualTranslationWithExplicitTargetLanguage() throws Exception {
        when(fragments.save(7L, 9L, "rus", "Перевод"))
                .thenReturn(new FragmentResponse(9L, 7L, 4, "Original", "Перевод", 1));

        mvc.perform(put("/api/v1/books/7/fragments/9/translation")
                        .contentType(MediaType.APPLICATION_JSON)
                        .content("""
                                {"targetLanguage":"rus","translatedText":"Перевод"}
                                """))
                .andExpect(status().isOk())
                .andExpect(jsonPath("$.translatedText").value("Перевод"));
    }
}

