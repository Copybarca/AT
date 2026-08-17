package io.copybarca.transapi.restclient;

import io.copybarca.transapi.dto.client.PdfBuildRequest;
import java.util.Optional;

public interface PdfBuilderClient {

    Optional<?> build(PdfBuildRequest request);
}
