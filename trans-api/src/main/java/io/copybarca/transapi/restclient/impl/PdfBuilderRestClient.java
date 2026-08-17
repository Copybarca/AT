package io.copybarca.transapi.restclient.impl;

import io.copybarca.transapi.dto.client.PdfBuildRequest;
import io.copybarca.transapi.restclient.PdfBuilderClient;
import java.util.Optional;
import org.springframework.beans.factory.annotation.Value;
import org.springframework.stereotype.Component;
import org.springframework.web.client.RestClient;

@Component
public class PdfBuilderRestClient implements PdfBuilderClient {

    private final RestClient restClient;
    private final String buildPath;

    public PdfBuilderRestClient(
            @Value("${clients.pdf-builder.base-url}") String baseUrl,
            @Value("${clients.pdf-builder.build-path}") String buildPath
    ) {
        this.restClient = RestClient.builder().baseUrl(baseUrl).build();
        this.buildPath = buildPath;
    }

    @Override
    public Optional<?> build(PdfBuildRequest request) {
        Object response = restClient.post()
                .uri(buildPath)
                .body(request)
                .retrieve()
                .body(Object.class);
        return Optional.ofNullable(response);
    }
}
