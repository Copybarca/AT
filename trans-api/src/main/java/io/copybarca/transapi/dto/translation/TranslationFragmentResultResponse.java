package io.copybarca.transapi.dto.translation;

import io.copybarca.transapi.model.ProcessStatus;
import java.util.List;

public record TranslationFragmentResultResponse(
        boolean accepted,
        ProcessStatus processStatus,
        List<String> issues
) {
}
