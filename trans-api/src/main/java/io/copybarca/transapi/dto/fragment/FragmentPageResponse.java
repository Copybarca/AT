package io.copybarca.transapi.dto.fragment;

import java.util.List;

public record FragmentPageResponse(
        List<FragmentResponse> items,
        Integer nextSequence
) {
}
