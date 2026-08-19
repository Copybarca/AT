package io.copybarca.transapi.restclient;

import io.copybarca.transapi.dto.client.BuildAcceptedResponse;
import io.copybarca.transapi.dto.client.PdfBuildAsset;
import io.copybarca.transapi.dto.client.PdfBuildRequest;
import java.util.List;

public interface PdfBuilderClient {

    BuildAcceptedResponse build(
            PdfBuildRequest request,
            List<PdfBuildAsset> assets
    );
}
