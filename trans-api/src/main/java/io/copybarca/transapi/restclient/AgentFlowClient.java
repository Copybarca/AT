package io.copybarca.transapi.restclient;

import io.copybarca.transapi.dto.client.TranslateTextRequest;
import io.copybarca.transapi.dto.client.TranslateTextResponse;

public interface AgentFlowClient {

    TranslateTextResponse translate(TranslateTextRequest request);
}
