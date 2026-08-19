package io.copybarca.transapi.service;

import static org.junit.jupiter.api.Assertions.assertEquals;

import static org.junit.jupiter.api.Assertions.assertTrue;
import java.time.Duration;
import java.util.concurrent.CountDownLatch;
import java.util.concurrent.TimeUnit;
import org.junit.jupiter.api.Test;

class PipelineTaskQueueTest {

    @Test
    void boundsQueueAndDistinguishesDuplicateFromConflict() throws Exception {
        CountDownLatch started = new CountDownLatch(1);
        CountDownLatch release = new CountDownLatch(1);
        try (PipelineTaskQueue queue = new PipelineTaskQueue(1, 1)) {
            assertEquals(
                    QueueSubmitOutcome.ACCEPTED,
                    queue.submit("process-1", "same", () -> {
                        started.countDown();
                        await(release);
                    })
            );
            assertEquals(
                    QueueSubmitOutcome.DUPLICATE,
                    queue.submit("process-1", "same", () -> {
                    })
            );
            assertEquals(
                    QueueSubmitOutcome.CONFLICT,
                    queue.submit("process-1", "different", () -> {
                    })
            );
            assertTrue(started.await(1, TimeUnit.SECONDS));
            assertEquals(
                    QueueSubmitOutcome.ACCEPTED,
                    queue.submit("process-2", "two", () -> {
                    })
            );
            assertEquals(
                    QueueSubmitOutcome.FULL,
                    queue.submit("process-3", "three", () -> {
                    })
            );
            release.countDown();
        }
    }

    @Test
    void failedTaskCanBeRetried() throws Exception {
        CountDownLatch failed = new CountDownLatch(1);
        CountDownLatch completed = new CountDownLatch(1);
        try (PipelineTaskQueue queue = new PipelineTaskQueue(1, 1)) {
            assertEquals(
                    QueueSubmitOutcome.ACCEPTED,
                    queue.submit("process-1", "same", () -> {
                        failed.countDown();
                        throw new IllegalStateException("synthetic");
                    })
            );
            assertTrue(failed.await(1, TimeUnit.SECONDS));
            awaitCondition(() ->
                    queue.submit("process-1", "same", completed::countDown)
                            == QueueSubmitOutcome.ACCEPTED
            );
            assertTrue(completed.await(1, TimeUnit.SECONDS));
            assertEquals(0, completed.getCount());
        }
    }

    private static void await(CountDownLatch latch) {
        try {
            latch.await();
        } catch (InterruptedException exception) {
            Thread.currentThread().interrupt();
            throw new IllegalStateException(exception);
        }
    }

    private static void awaitCondition(Check check) throws Exception {
        long deadline = System.nanoTime() + TimeUnit.SECONDS.toNanos(1);
        while (System.nanoTime() < deadline) {
            if (check.evaluate()) {
                return;
            }
            Thread.onSpinWait();
        }
        throw new AssertionError("Condition was not satisfied");
    }

    @FunctionalInterface
    private interface Check {
        boolean evaluate();
    }
}
