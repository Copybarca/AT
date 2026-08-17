package io.copybarca.transapi.restclient.impl;

import io.copybarca.transapi.dto.client.TranslateTextRequest;
import io.copybarca.transapi.restclient.AgentFlowClient;
import java.util.Optional;
import org.springframework.beans.factory.annotation.Value;
import org.springframework.stereotype.Component;
import org.springframework.web.client.RestClient;

@Component
public class AgentFlowRestClient implements AgentFlowClient {

    private final RestClient restClient;
    private final String translatePath;

    public AgentFlowRestClient(
            @Value("${clients.agent-flow.base-url}") String baseUrl,
            @Value("${clients.agent-flow.translate-path}") String translatePath
    ) {
        this.restClient = RestClient.builder().baseUrl(baseUrl).build();
        this.translatePath = translatePath;
    }

    @Override
    public Optional<?> translate(TranslateTextRequest request) {
        Object response = restClient.post()
                .uri(translatePath)
                .body(request)
                .retrieve()
                .body(Object.class);
        return Optional.ofNullable(response);
    }
}
