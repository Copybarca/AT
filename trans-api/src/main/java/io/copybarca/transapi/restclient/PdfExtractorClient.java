package io.copybarca.transapi.restclient;

import io.copybarca.transapi.dto.client.PdfExtractRequest;
import java.util.Optional;

public interface PdfExtractorClient {

    Optional<?> extract(PdfExtractRequest request);
}
