package io.copybarca.transapi.service;

public enum QueueSubmitOutcome {
    ACCEPTED,
    DUPLICATE,
    CONFLICT,
    FULL
}
