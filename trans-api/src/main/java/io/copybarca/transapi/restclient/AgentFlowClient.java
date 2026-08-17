package io.copybarca.transapi.restclient;

import io.copybarca.transapi.dto.client.TranslateTextRequest;
import java.util.Optional;

public interface AgentFlowClient {

    Optional<?> translate(TranslateTextRequest request);
}
