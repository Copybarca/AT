package io.copybarca.transapi.service;

public class PipelineQueueFullException extends RuntimeException {

    public PipelineQueueFullException() {
        super("Pipeline task queue is full");
    }
}
