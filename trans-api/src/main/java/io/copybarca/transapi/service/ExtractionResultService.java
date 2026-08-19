package io.copybarca.transapi.service;

import io.copybarca.transapi.dto.extraction.ExtractionCompleteRequest;
import io.copybarca.transapi.dto.extraction.ExtractionImageRequest;
import io.copybarca.transapi.dto.extraction.ExtractionRegionBatchRequest;
import io.copybarca.transapi.dto.extraction.ExtractionRegionData;
import io.copybarca.transapi.dto.extraction.ExtractionSegmentBatchRequest;
import io.copybarca.transapi.dto.extraction.ExtractionSegmentData;
import io.copybarca.transapi.model.Book;
import io.copybarca.transapi.model.Insertion;
import io.copybarca.transapi.model.InsertionTextRegion;
import io.copybarca.transapi.model.PdfExtractionProcess;
import io.copybarca.transapi.model.Segment;
import io.copybarca.transapi.model.TextSegment;
import io.copybarca.transapi.repo.BookRepository;
import io.copybarca.transapi.repo.InsertionRepository;
import io.copybarca.transapi.repo.InsertionTextRegionRepository;
import io.copybarca.transapi.repo.PdfExtractionProcessRepository;
import io.copybarca.transapi.repo.SegmentRepository;
import io.copybarca.transapi.repo.TextSegmentRepository;
import java.io.IOException;
import java.io.InputStream;
import java.security.MessageDigest;
import java.security.NoSuchAlgorithmException;
import java.util.HexFormat;
import org.springframework.stereotype.Service;
import org.springframework.transaction.annotation.Transactional;
import org.springframework.web.multipart.MultipartFile;

@Service
public class ExtractionResultService {

    private final BookRepository books;
    private final PdfExtractionProcessRepository processes;
    private final TextSegmentRepository texts;
    private final SegmentRepository segments;
    private final InsertionRepository insertions;
    private final InsertionTextRegionRepository regions;
    private final BookFileStorage storage;

    public ExtractionResultService(
            BookRepository books,
            PdfExtractionProcessRepository processes,
            TextSegmentRepository texts,
            SegmentRepository segments,
            InsertionRepository insertions,
            InsertionTextRegionRepository regions,
            BookFileStorage storage
    ) {
        this.books = books;
        this.processes = processes;
        this.texts = texts;
        this.segments = segments;
        this.insertions = insertions;
        this.regions = regions;
        this.storage = storage;
    }

    @Transactional
    public void upsertSegments(Long bookId, ExtractionSegmentBatchRequest request) {
        requireProcess(bookId, request.processId());
        Book book = books.findById(bookId)
                .orElseThrow(() -> new IllegalArgumentException("Book does not exist"));
        for (ExtractionSegmentData data : request.segments()) {
            TextSegment text = upsertText(data.sourceHash(), data.text());
            Segment segment = segments.findByBookIdAndStableKey(bookId, data.stableKey())
                    .orElseGet(() -> new Segment(
                            book,
                            data.stableKey(),
                            data.sequentialNumber()
                    ));
            segment.applyTextExtraction(
                    text,
                    data.sequentialNumber(),
                    data.physicalPage(),
                    data.bbox().toJson(),
                    data.style(),
                    data.translatable()
            );
            segments.save(segment);
        }
    }

    @Transactional
    public void storeImage(
            Long bookId,
            ExtractionImageRequest request,
            MultipartFile file
    ) {
        requireProcess(bookId, request.processId());
        Book book = books.findById(bookId)
                .orElseThrow(() -> new IllegalArgumentException("Book does not exist"));
        String checksum = checksum(file);
        Segment segment = segments.findByBookIdAndStableKey(bookId, request.stableKey())
                .orElseGet(() -> new Segment(
                        book,
                        request.stableKey(),
                        request.sequentialNumber()
                ));
        if (segment.getInsertion() != null
                && checksum.equals(segment.getInsertion().getChecksum())) {
            return;
        }

        String path = storage.storeAsset(bookId, file);
        Insertion insertion = insertions.save(
                new Insertion(path, request.mediaType(), checksum)
        );
        segment.applyImageExtraction(
                insertion,
                request.sequentialNumber(),
                request.physicalPage(),
                request.bbox().toJson()
        );
        segments.save(segment);
    }

    @Transactional
    public void upsertRegions(Long bookId, ExtractionRegionBatchRequest request) {
        requireProcess(bookId, request.processId());
        for (ExtractionRegionData data : request.regions()) {
            Segment image = segments.findByBookIdAndStableKey(
                            bookId,
                            data.imageStableKey()
                    )
                    .filter(candidate -> candidate.getInsertion() != null)
                    .orElseThrow(() -> new IllegalArgumentException(
                            "Image position does not exist"
                    ));
            if (regions.findByStableKey(data.stableKey()).isPresent()) {
                continue;
            }
            TextSegment text = upsertText(data.sourceHash(), data.text());
            regions.save(
                    new InsertionTextRegion(
                            image.getInsertion(),
                            data.stableKey(),
                            text,
                            data.sequentialNumber(),
                            data.bbox().toJson(),
                            data.confidence()
                    )
            );
        }
    }

    @Transactional
    public void complete(Long bookId, ExtractionCompleteRequest request) {
        PdfExtractionProcess process = requireProcess(bookId, request.processId());

        long actualSegments = segments.countTextPositions(bookId);
        long actualImages = segments.countImagePositions(bookId);
        long actualRegions = regions.countByBookId(bookId);
        if (actualSegments != request.expectedSegmentCount()
                || actualImages != request.expectedImageCount()
                || actualRegions != request.expectedRegionCount()) {
            throw new ExtractionCountMismatchException(
                    actualSegments,
                    actualImages,
                    actualRegions
            );
        }

        process.recordManifest(
                request.pdfSha256(),
                request.extractorVersion(),
                request.expectedSegmentCount(),
                request.expectedImageCount(),
                request.expectedRegionCount()
        );
        process.complete();
    }

    private PdfExtractionProcess requireProcess(Long bookId, Long processId) {
        return processes.findById(processId)
                .filter(candidate -> candidate.getBookId().equals(bookId))
                .orElseThrow(() -> new IllegalArgumentException(
                        "Extraction process does not belong to book"
                ));
    }

    private TextSegment upsertText(String sourceHash, String value) {
        return texts.findById(sourceHash)
                .map(existing -> {
                    if (!existing.getText().equals(value)) {
                        throw new IllegalArgumentException(
                                "Source hash is already associated with different text"
                        );
                    }
                    return existing;
                })
                .orElseGet(() -> texts.save(new TextSegment(sourceHash, value)));
    }

    private static String checksum(MultipartFile file) {
        try (InputStream input = file.getInputStream()) {
            MessageDigest digest = MessageDigest.getInstance("SHA-256");
            byte[] buffer = new byte[8192];
            int length;
            while ((length = input.read(buffer)) >= 0) {
                digest.update(buffer, 0, length);
            }
            return "sha256:" + HexFormat.of().formatHex(digest.digest());
        } catch (IOException | NoSuchAlgorithmException exception) {
            throw new IllegalArgumentException("Could not calculate image checksum", exception);
        }
    }
}
