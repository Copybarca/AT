package io.copybarca.transapi.restclient;

import io.copybarca.transapi.dto.client.ExtractionAcceptedResponse;
import io.copybarca.transapi.dto.client.PdfExtractRequest;

public interface PdfExtractorClient {

    ExtractionAcceptedResponse extract(PdfExtractRequest request, byte[] pdf);
}
