package io.copybarca.transapi.restclient.impl;

import io.copybarca.transapi.dto.client.BuildAcceptedResponse;
import io.copybarca.transapi.dto.client.PdfBuildAsset;
import io.copybarca.transapi.dto.client.PdfBuildRequest;
import io.copybarca.transapi.restclient.PdfBuilderClient;
import java.util.List;
import org.springframework.beans.factory.annotation.Value;
import org.springframework.core.io.ByteArrayResource;
import org.springframework.http.HttpEntity;
import org.springframework.http.HttpHeaders;
import org.springframework.http.MediaType;
import org.springframework.http.client.MultipartBodyBuilder;
import org.springframework.stereotype.Component;
import org.springframework.web.client.RestClient;

@Component
public class PdfBuilderRestClient implements PdfBuilderClient {

    private final RestClient restClient;
    private final String buildPath;
    private final String serviceToken;

    public PdfBuilderRestClient(
            @Value("${clients.pdf-builder.base-url}") String baseUrl,
            @Value("${clients.pdf-builder.build-path}") String buildPath,
            @Value("${internal.service-token}") String serviceToken
    ) {
        this.restClient = RestClient.builder().baseUrl(baseUrl).build();
        this.buildPath = buildPath;
        this.serviceToken = serviceToken;
    }

    @Override
    public BuildAcceptedResponse build(
            PdfBuildRequest request,
            List<PdfBuildAsset> assets
    ) {
        MultipartBodyBuilder multipart = new MultipartBodyBuilder();
        multipart.part("request", request)
                .contentType(MediaType.APPLICATION_JSON);
        for (PdfBuildAsset asset : assets) {
            HttpHeaders headers = new HttpHeaders();
            headers.setContentType(MediaType.parseMediaType(asset.mediaType()));
            headers.set("X-Asset-Key", asset.assetKey());
            multipart.part(
                    "asset",
                    new HttpEntity<>(
                            new NamedByteArrayResource(
                                    asset.content(),
                                    asset.assetKey()
                            ),
                            headers
                    )
            );
        }

        BuildAcceptedResponse response = restClient.post()
                .uri(buildPath)
                .header(HttpHeaders.AUTHORIZATION, "Bearer " + serviceToken)
                .header("Idempotency-Key", "build-" + request.processId())
                .contentType(MediaType.MULTIPART_FORM_DATA)
                .body(multipart.build())
                .retrieve()
                .body(BuildAcceptedResponse.class);
        if (response == null) {
            throw new IllegalStateException("PDF builder returned no response");
        }
        return response;
    }

    private static final class NamedByteArrayResource extends ByteArrayResource {

        private final String filename;

        private NamedByteArrayResource(byte[] content, String assetKey) {
            super(content);
            this.filename = assetKey + ".bin";
        }

        @Override
        public String getFilename() {
            return filename;
        }
    }
}
