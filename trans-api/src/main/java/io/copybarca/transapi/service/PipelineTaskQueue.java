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
import java.util.function.Consumer;
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
        return submit(taskKey, fingerprint, task, ignored -> {
        });
    }

    public QueueSubmitOutcome submit(
            String taskKey,
            String fingerprint,
            Runnable task,
            Consumer<Throwable> failureHandler
    ) {
        String existing = fingerprints.putIfAbsent(taskKey, fingerprint);
        if (existing != null) {
            return existing.equals(fingerprint)
                    ? QueueSubmitOutcome.DUPLICATE
                    : QueueSubmitOutcome.CONFLICT;
        }

        try {
            executor.execute(() -> execute(taskKey, fingerprint, task, failureHandler));
            return QueueSubmitOutcome.ACCEPTED;
        } catch (RejectedExecutionException exception) {
            fingerprints.remove(taskKey, fingerprint);
            return QueueSubmitOutcome.FULL;
        }
    }

    private void execute(
            String taskKey,
            String fingerprint,
            Runnable task,
            Consumer<Throwable> failureHandler
    ) {
        try {
            task.run();
        } catch (RuntimeException | Error exception) {
            LOGGER.error("Pipeline task {} failed", taskKey, exception);
            try {
                failureHandler.accept(exception);
            } catch (RuntimeException | Error failureException) {
                LOGGER.error(
                        "Could not persist failure for pipeline task {}",
                        taskKey,
                        failureException
                );
            }
        } finally {
            // Dedupe only queued/running local work. Downstream commands have a
            // stable Idempotency-Key, and fragment callbacks must schedule the
            // same process key again for the next SQL row.
            fingerprints.remove(taskKey, fingerprint);
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
