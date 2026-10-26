package com.xenoamess.vivhite_video_framework.maker;

import java.io.IOException;
import java.io.OutputStream;
import java.nio.charset.StandardCharsets;
import java.time.Duration;
import java.util.List;
import java.util.concurrent.Executors;
import java.util.concurrent.TimeUnit;

/** A bounded, shell-free process, including blocked encoder pipe writes. */
final class MediaProcess {
    @FunctionalInterface
    interface InputWriter { void write(OutputStream stream) throws Exception; }

    private MediaProcess() { }

    static String run(List<String> command, Duration timeout, InputWriter input) throws Exception {
        ProcessBuilder builder = new ProcessBuilder(command);
        builder.environment().put("PYTHONUTF8", "1");
        Process process = builder.start();
        try (var executor = Executors.newVirtualThreadPerTaskExecutor()) {
            var stdout = executor.submit(() -> process.getInputStream().readAllBytes());
            var stderr = executor.submit(() -> process.getErrorStream().readAllBytes());
            var writer = executor.submit(() -> {
                try (var stream = process.getOutputStream()) {
                    if (input != null) { input.write(stream); }
                }
                return true;
            });
            try {
                if (!process.waitFor(timeout.toMillis(), TimeUnit.MILLISECONDS)) {
                    throw new IOException("Process timed out: " + command.getFirst());
                }
                String error = new String(stderr.get(), StandardCharsets.UTF_8);
                if (process.exitValue() != 0) {
                    throw new IOException(command.getFirst() + " failed: " + error.substring(0, Math.min(6000, error.length())));
                }
                writer.get();
                return new String(stdout.get(), StandardCharsets.UTF_8);
            } finally {
                stop(process);
                writer.cancel(true);
            }
        }
    }

    static String run(List<String> command, Duration timeout) throws Exception {
        return run(command, timeout, null);
    }

    private static void stop(Process process) {
        if (process.isAlive()) {
            process.descendants().forEach(ProcessHandle::destroyForcibly);
            process.destroyForcibly();
        }
    }
}
