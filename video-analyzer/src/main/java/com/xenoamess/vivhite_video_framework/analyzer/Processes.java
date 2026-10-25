package com.xenoamess.vivhite_video_framework.analyzer;

import java.io.IOException;
import java.nio.charset.StandardCharsets;
import java.time.Duration;
import java.util.List;
import java.util.concurrent.Executors;
import java.util.concurrent.TimeUnit;

final class Processes {
    private Processes() { }

    static String capture(List<String> command, Duration timeout) throws Exception {
        Process process = new ProcessBuilder(command).start();
        process.getOutputStream().close();
        try (var executor = Executors.newVirtualThreadPerTaskExecutor()) {
            var stdout = executor.submit(() -> process.getInputStream().readAllBytes());
            var stderr = executor.submit(() -> process.getErrorStream().readAllBytes());
            try {
                if (!process.waitFor(timeout.toMillis(), TimeUnit.MILLISECONDS)) {
                    throw new IOException("Process timed out: " + command.getFirst());
                }
                String error = new String(stderr.get(), StandardCharsets.UTF_8);
                if (process.exitValue() != 0) {
                    throw new IOException(command.getFirst() + " failed: " + error.substring(0, Math.min(4000, error.length())));
                }
                return new String(stdout.get(), StandardCharsets.UTF_8);
            } finally {
                destroy(process);
            }
        }
    }

    static void live(List<String> command, Duration timeout) throws Exception {
        ProcessBuilder builder = new ProcessBuilder(command).inheritIO();
        builder.environment().put("PYTHONUTF8", "1");
        builder.environment().put("HF_HUB_DISABLE_XET", "1");
        Process process = builder.start();
        try {
            if (!process.waitFor(timeout.toMillis(), TimeUnit.MILLISECONDS)) {
                throw new IOException("Inference timed out: " + command.getFirst());
            }
            if (process.exitValue() != 0) {
                throw new IOException("Inference failed with exit code " + process.exitValue());
            }
        } finally {
            destroy(process);
        }
    }

    private static void destroy(Process process) {
        if (process.isAlive()) {
            process.descendants().forEach(ProcessHandle::destroyForcibly);
            process.destroyForcibly();
        }
    }
}
