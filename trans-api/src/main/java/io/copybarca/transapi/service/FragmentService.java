package io.copybarca.transapi.service;

import io.copybarca.transapi.dto.fragment.FragmentPageResponse;
import io.copybarca.transapi.dto.fragment.FragmentResponse;
import io.copybarca.transapi.model.Segment;
import io.copybarca.transapi.model.TranslatedSegment;
import io.copybarca.transapi.model.TranslatedSegmentId;
import io.copybarca.transapi.repo.BookRepository;
import io.copybarca.transapi.repo.PdfBuildProcessRepository;
import io.copybarca.transapi.repo.SegmentRepository;
import io.copybarca.transapi.repo.TranslatedSegmentRepository;
import io.copybarca.transapi.service.exception.BookNotFoundException;
import java.util.ArrayList;
import java.util.List;
import org.springframework.stereotype.Service;
import org.springframework.transaction.annotation.Transactional;
import org.springframework.util.StringUtils;

@Service
public class FragmentService {

    private final BookRepository books;
    private final SegmentRepository segments;
    private final TranslatedSegmentRepository translations;
    private final PdfBuildProcessRepository builds;

    public FragmentService(
            BookRepository books,
            SegmentRepository segments,
            TranslatedSegmentRepository translations,
            PdfBuildProcessRepository builds
    ) {
        this.books = books;
        this.segments = segments;
        this.translations = translations;
        this.builds = builds;
    }

    @Transactional(readOnly = true)
    public FragmentPageResponse page(
            Long bookId,
            String targetLanguage,
            String filter,
            Integer afterSequence,
            int limit
    ) {
        if (!books.existsById(bookId)) {
            throw new BookNotFoundException(bookId);
        }
        String language = requireLanguage(targetLanguage);
        if (limit < 1 || limit > 100) {
            throw new IllegalArgumentException("Fragment limit must be between 1 and 100");
        }
        String requestedFilter = filter == null ? "all" : filter;
        if (!requestedFilter.equals("all") && !requestedFilter.equals("untranslated")) {
            throw new IllegalArgumentException("Fragment filter must be all or untranslated");
        }
        int cursor = afterSequence == null ? 0 : afterSequence;
        List<FragmentResponse> eligible = new ArrayList<>();
        for (Segment segment : segments.findByBook_IdOrderBySequentialNumber(bookId)) {
            if (segment.getTextSegment() == null || segment.getSequentialNumber() <= cursor) {
                continue;
            }
            var id = new TranslatedSegmentId(
                    segment.getTextSegment().getTextHash(),
                    language
            );
            var translated = translations.findById(id).orElse(null);
            if (requestedFilter.equals("untranslated") && translated != null) {
                continue;
            }
            eligible.add(toResponse(segment, translated));
            if (eligible.size() > limit) {
                break;
            }
        }
        boolean hasMore = eligible.size() > limit;
        List<FragmentResponse> items = hasMore
                ? List.copyOf(eligible.subList(0, limit))
                : List.copyOf(eligible);
        Integer next = hasMore ? items.getLast().sequence() : null;
        return new FragmentPageResponse(items, next);
    }

    @Transactional
    public FragmentResponse save(
            Long bookId,
            Long fragmentId,
            String targetLanguage,
            String translatedText
    ) {
        String language = requireLanguage(targetLanguage);
        if (!StringUtils.hasText(translatedText)) {
            throw new IllegalArgumentException("Translation must not be blank");
        }
        Segment segment = segments.findById(fragmentId)
                .filter(candidate -> candidate.getBook().getId().equals(bookId))
                .orElseThrow(() -> new IllegalArgumentException(
                        "Fragment does not belong to book"
                ));
        if (segment.getTextSegment() == null || !segment.isTranslatable()) {
            throw new IllegalArgumentException("Fragment is not translatable");
        }
        var id = new TranslatedSegmentId(
                segment.getTextSegment().getTextHash(),
                language
        );
        TranslatedSegment value = translations.findById(id)
                .orElseGet(() -> new TranslatedSegment(
                        segment.getTextSegment(),
                        language,
                        translatedText.trim()
                ));
        value.setTranslation(translatedText.trim());
        translations.save(value);

        segment.getBook().setTranslatedPath(null);
        builds.findByBook_IdAndTargetLanguage(bookId, language)
                .ifPresent(builds::delete);
        return toResponse(segment, value);
    }

    private static String requireLanguage(String language) {
        if (!StringUtils.hasText(language) || language.trim().length() > 32) {
            throw new IllegalArgumentException("Target language is required");
        }
        return language.trim();
    }

    private static FragmentResponse toResponse(
            Segment segment,
            TranslatedSegment translation
    ) {
        return new FragmentResponse(
                segment.getId(),
                segment.getBook().getId(),
                segment.getSequentialNumber(),
                segment.getTextSegment().getText(),
                translation == null ? null : translation.getTranslation(),
                translation == null ? 0 : 1
        );
    }
}
