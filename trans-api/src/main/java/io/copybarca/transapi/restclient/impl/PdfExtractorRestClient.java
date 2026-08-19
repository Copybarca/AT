package io.copybarca.transapi.restclient.impl;

import io.copybarca.transapi.dto.client.ExtractionAcceptedResponse;
import io.copybarca.transapi.dto.client.PdfExtractRequest;
import io.copybarca.transapi.restclient.PdfExtractorClient;
import org.springframework.beans.factory.annotation.Value;
import org.springframework.core.io.ByteArrayResource;
import org.springframework.http.HttpHeaders;
import org.springframework.http.MediaType;
import org.springframework.stereotype.Component;
import org.springframework.util.LinkedMultiValueMap;
import org.springframework.util.MultiValueMap;
import org.springframework.web.client.RestClient;

@Component
public class PdfExtractorRestClient implements PdfExtractorClient {

    private final RestClient restClient;
    private final String extractPath;
    private final String serviceToken;

    public PdfExtractorRestClient(
            @Value("${clients.pdf-extractor.base-url}") String baseUrl,
            @Value("${clients.pdf-extractor.extract-path}") String extractPath,
            @Value("${internal.service-token}") String serviceToken
    ) {
        this.restClient = RestClient.builder().baseUrl(baseUrl).build();
        this.extractPath = extractPath;
        this.serviceToken = serviceToken;
    }

    @Override
    public ExtractionAcceptedResponse extract(PdfExtractRequest request, byte[] pdf) {
        MultiValueMap<String, Object> multipart = new LinkedMultiValueMap<>();
        multipart.add("request", request);
        multipart.add("file", new ByteArrayResource(pdf) {
            @Override
            public String getFilename() {
                return "book.pdf";
            }
        });

        ExtractionAcceptedResponse response = restClient.post()
                .uri(extractPath)
                .header(HttpHeaders.AUTHORIZATION, "Bearer " + serviceToken)
                .header(
                        "Idempotency-Key",
                        "extraction-" + request.processId()
                )
                .contentType(MediaType.MULTIPART_FORM_DATA)
                .body(multipart)
                .retrieve()
                .body(ExtractionAcceptedResponse.class);
        if (response == null) {
            throw new IllegalStateException("PDF extractor returned an empty response");
        }
        return response;
    }
}
