package io.copybarca.transapi.dto.process;

import io.copybarca.transapi.model.ProcessStatus;
import java.math.BigDecimal;

public record TranslationStatusResponse(
        ProcessStatus status,
        long totalFragments,
        long translatedFragments,
        BigDecimal percent
) {
}
