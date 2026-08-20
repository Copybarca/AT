package io.copybarca.transapi.restclient;

import io.copybarca.transapi.dto.client.TranslateTextRequest;
import io.copybarca.transapi.dto.client.TranslationDispatchAcceptedResponse;

public interface AgentFlowClient {

    TranslationDispatchAcceptedResponse submit(TranslateTextRequest request);
}
