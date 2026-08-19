package io.copybarca.transapi.service;

import io.copybarca.transapi.dto.client.PdfBuildAsset;
import io.copybarca.transapi.dto.client.PdfBuildDocument;
import io.copybarca.transapi.dto.client.PdfBuildElement;
import io.copybarca.transapi.dto.client.PdfBuildRequest;
import io.copybarca.transapi.model.Book;
import io.copybarca.transapi.model.PdfBuildProcess;
import io.copybarca.transapi.model.Segment;
import io.copybarca.transapi.model.TranslatedSegmentId;
import io.copybarca.transapi.repo.BookRepository;
import io.copybarca.transapi.repo.PdfBuildProcessRepository;
import io.copybarca.transapi.repo.SegmentRepository;
import io.copybarca.transapi.repo.TranslatedSegmentRepository;
import io.copybarca.transapi.restclient.PdfBuilderClient;
import java.util.ArrayList;
import java.util.List;
import org.springframework.stereotype.Service;
import org.springframework.transaction.annotation.Transactional;

@Service
public class PdfBuildDispatchService {

    private final PdfBuildProcessRepository processes;
    private final BookRepository books;
    private final SegmentRepository segments;
    private final TranslatedSegmentRepository translations;
    private final BookFileStorage storage;
    private final PdfBuilderClient builder;

    public PdfBuildDispatchService(
            PdfBuildProcessRepository processes,
            BookRepository books,
            SegmentRepository segments,
            TranslatedSegmentRepository translations,
            BookFileStorage storage,
            PdfBuilderClient builder
    ) {
        this.processes = processes;
        this.books = books;
        this.segments = segments;
        this.translations = translations;
        this.storage = storage;
        this.builder = builder;
    }

    @Transactional(readOnly = true)
    public void dispatch(Long processId) {
        PdfBuildProcess process = processes.findById(processId)
                .orElseThrow(() -> new IllegalArgumentException(
                        "PDF build process does not exist"
                ));
        Book book = books.findById(process.getBookId()).orElseThrow();
        List<PdfBuildElement> elements = new ArrayList<>();
        List<PdfBuildAsset> assets = new ArrayList<>();

        for (Segment segment : segments.findByBookIdOrderBySequentialNumber(
                book.getId()
        )) {
            if (segment.getTextSegment() != null) {
                String text = segment.isTranslatable()
                        ? translations.findById(
                                        new TranslatedSegmentId(
                                                segment.getTextSegment().getTextHash(),
                                                process.getTargetLanguage()
                                        )
                                )
                                .orElseThrow(() -> new IllegalStateException(
                                        "Build cannot start with missing translation"
                                ))
                                .getTranslation()
                        : segment.getTextSegment().getText();
                elements.add(
                        PdfBuildElement.text(
                                segment.getSequentialNumber(),
                                text,
                                segment.getStyle() == null
                                        ? "BODY"
                                        : segment.getStyle()
                        )
                );
            } else if (segment.getInsertion() != null) {
                String assetKey = segment.getStableKey();
                elements.add(
                        PdfBuildElement.image(
                                segment.getSequentialNumber(),
                                assetKey,
                                segment.getInsertion().getMediaType()
                        )
                );
                assets.add(
                        new PdfBuildAsset(
                                assetKey,
                                segment.getInsertion().getMediaType(),
                                storage.read(segment.getInsertion().getPath())
                        )
                );
            }
        }

        builder.build(
                new PdfBuildRequest(
                        process.getId(),
                        book.getId(),
                        "/internal/v1/books/" + book.getId() + "/build-result",
                        new PdfBuildDocument(
                                book.getTitle(),
                                process.getTargetLanguage()
                        ),
                        List.copyOf(elements)
                ),
                List.copyOf(assets)
        );
    }
}
