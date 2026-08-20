package io.copybarca.transapi.restclient.impl;

import io.copybarca.transapi.dto.client.TranslateTextRequest;
import io.copybarca.transapi.dto.client.TranslationDispatchAcceptedResponse;
import io.copybarca.transapi.restclient.AgentFlowClient;
import org.springframework.beans.factory.annotation.Value;
import org.springframework.http.HttpHeaders;
import org.springframework.stereotype.Component;
import org.springframework.web.client.RestClient;

@Component
public class AgentFlowRestClient implements AgentFlowClient {

    private final RestClient restClient;
    private final String translatePath;
    private final String serviceToken;

    public AgentFlowRestClient(
            @Value("${clients.agent-flow.base-url}") String baseUrl,
            @Value("${clients.agent-flow.translate-path}") String translatePath,
            @Value("${internal.service-token}") String serviceToken
    ) {
        this.restClient = RestClient.builder().baseUrl(baseUrl).build();
        this.translatePath = translatePath;
        this.serviceToken = serviceToken;
    }

    @Override
    public TranslationDispatchAcceptedResponse submit(TranslateTextRequest request) {
        TranslationDispatchAcceptedResponse response = restClient.post()
                .uri(translatePath)
                .header(HttpHeaders.AUTHORIZATION, "Bearer " + serviceToken)
                .header(
                        "Idempotency-Key",
                        "translation-" + request.processId() + "-" + request.segmentId()
                )
                .body(request)
                .retrieve()
                .body(TranslationDispatchAcceptedResponse.class);
        if (response == null) {
            throw new IllegalStateException("Translation service returned no response");
        }
        if (!response.accepted()
                || !request.requestId().equals(response.requestId())
                || !request.processId().equals(response.processId())
                || !request.segmentId().equals(response.segmentId())) {
            throw new IllegalStateException("Translation service returned invalid acceptance");
        }
        return response;
    }
}
