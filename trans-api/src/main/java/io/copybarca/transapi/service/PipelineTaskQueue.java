package io.copybarca.transapi.service;

import jakarta.annotation.PreDestroy;
import java.time.Duration;
import java.util.Map;
import java.util.concurrent.ArrayBlockingQueue;
import java.util.concurrent.ConcurrentHashMap;
import java.util.concurrent.RejectedExecutionException;
import java.util.concurrent.ThreadPoolExecutor;
import java.util.concurrent.TimeUnit;
import java.util.concurrent.atomic.AtomicInteger;
import org.slf4j.Logger;
import org.slf4j.LoggerFactory;
import org.springframework.beans.factory.annotation.Value;
import org.springframework.stereotype.Component;

@Component
public class PipelineTaskQueue implements AutoCloseable {

    private static final Logger LOGGER = LoggerFactory.getLogger(PipelineTaskQueue.class);
    private static final Duration SHUTDOWN_TIMEOUT = Duration.ofSeconds(5);

    private final ThreadPoolExecutor executor;
    private final Map<String, String> fingerprints = new ConcurrentHashMap<>();

    public PipelineTaskQueue(
            @Value("${pipeline.queue.capacity:16}") int capacity,
            @Value("${pipeline.queue.worker-count:2}") int workerCount
    ) {
        if (capacity < 1 || workerCount < 1) {
            throw new IllegalArgumentException("Queue capacity and worker count must be positive");
        }
        AtomicInteger threadNumber = new AtomicInteger();
        this.executor = new ThreadPoolExecutor(
                workerCount,
                workerCount,
                0L,
                TimeUnit.MILLISECONDS,
                new ArrayBlockingQueue<>(capacity),
                runnable -> {
                    Thread thread = new Thread(
                            runnable,
                            "pipeline-worker-" + threadNumber.incrementAndGet()
                    );
                    thread.setDaemon(true);
                    return thread;
                },
                new ThreadPoolExecutor.AbortPolicy()
        );
    }

    public QueueSubmitOutcome submit(
            String taskKey,
            String fingerprint,
            Runnable task
    ) {
        String existing = fingerprints.putIfAbsent(taskKey, fingerprint);
        if (existing != null) {
            return existing.equals(fingerprint)
                    ? QueueSubmitOutcome.DUPLICATE
                    : QueueSubmitOutcome.CONFLICT;
        }

        try {
            executor.execute(() -> execute(taskKey, fingerprint, task));
            return QueueSubmitOutcome.ACCEPTED;
        } catch (RejectedExecutionException exception) {
            fingerprints.remove(taskKey, fingerprint);
            return QueueSubmitOutcome.FULL;
        }
    }

    private void execute(String taskKey, String fingerprint, Runnable task) {
        try {
            task.run();
        } catch (RuntimeException | Error exception) {
            fingerprints.remove(taskKey, fingerprint);
            LOGGER.error("Pipeline task {} failed", taskKey, exception);
        }
    }

    @Override
    @PreDestroy
    public void close() {
        executor.shutdown();
        try {
            if (!executor.awaitTermination(
                    SHUTDOWN_TIMEOUT.toMillis(),
                    TimeUnit.MILLISECONDS
            )) {
                executor.shutdownNow();
            }
        } catch (InterruptedException exception) {
            Thread.currentThread().interrupt();
            executor.shutdownNow();
        }
    }
}
