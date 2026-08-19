package io.copybarca.transapi.service;

import io.copybarca.transapi.dto.client.PdfExtractRequest;
import io.copybarca.transapi.restclient.PdfExtractorClient;
import java.security.MessageDigest;
import java.security.NoSuchAlgorithmException;
import java.util.HexFormat;
import org.springframework.stereotype.Service;

@Service
public class PdfExtractionDispatchService {

    private final BookFileStorage storage;
    private final PdfExtractorClient extractor;

    public PdfExtractionDispatchService(
            BookFileStorage storage,
            PdfExtractorClient extractor
    ) {
        this.storage = storage;
        this.extractor = extractor;
    }

    public void dispatch(Long processId, Long bookId, String originalPath) {
        byte[] pdf = storage.read(originalPath);
        extractor.extract(
                new PdfExtractRequest(processId, bookId, sha256(pdf)),
                pdf
        );
    }

    private static String sha256(byte[] value) {
        try {
            MessageDigest digest = MessageDigest.getInstance("SHA-256");
            return "sha256:" + HexFormat.of().formatHex(digest.digest(value));
        } catch (NoSuchAlgorithmException exception) {
            throw new IllegalStateException("SHA-256 is not available", exception);
        }
    }
}
