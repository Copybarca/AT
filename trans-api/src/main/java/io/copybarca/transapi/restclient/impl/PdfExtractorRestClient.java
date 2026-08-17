package io.copybarca.transapi.restclient.impl;

import io.copybarca.transapi.dto.client.PdfExtractRequest;
import io.copybarca.transapi.restclient.PdfExtractorClient;
import java.util.Optional;
import org.springframework.beans.factory.annotation.Value;
import org.springframework.stereotype.Component;
import org.springframework.web.client.RestClient;

@Component
public class PdfExtractorRestClient implements PdfExtractorClient {

    private final RestClient restClient;
    private final String extractPath;

    public PdfExtractorRestClient(
            @Value("${clients.pdf-extractor.base-url}") String baseUrl,
            @Value("${clients.pdf-extractor.extract-path}") String extractPath
    ) {
        this.restClient = RestClient.builder().baseUrl(baseUrl).build();
        this.extractPath = extractPath;
    }

    @Override
    public Optional<?> extract(PdfExtractRequest request) {
        Object response = restClient.post()
                .uri(extractPath)
                .body(request)
                .retrieve()
                .body(Object.class);
        return Optional.ofNullable(response);
    }
}
