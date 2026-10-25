package com.xenoamess.vivhite_video_framework.analyzer;

import java.nio.file.Path;

public final class AnalyzerMain {
    private AnalyzerMain() { }

    public static void main(String[] args) {
        try {
            if ((args.length == 3 || args.length == 4 && args[3].equals("--reuse")) && args[0].equals("prepare")) {
                AnalysisPipeline.prepare(Path.of(args[1]), Path.of(args[2]),
                        args.length == 4 && args[3].equals("--reuse"));
            } else if (args.length == 3 && args[0].equals("import-review")) {
                ReviewService.importReview(Path.of(args[1]), Path.of(args[2]));
            } else if (args.length == 2 && args[0].equals("verify-puzzle")) {
                PuzzleExample.write(Path.of(args[1]));
            } else if (args.length == 2 && args[0].equals("review")) {
                new OpenAiReviewer().review(Path.of(args[1]));
            } else {
                throw new IllegalArgumentException("Usage: prepare CASE.json WORK_DIR [--reuse] | "
                        + "review WORK_DIR | import-review WORK_DIR REVIEW.json | verify-puzzle OUTPUT.json");
            }
        } catch (Exception exception) {
            System.err.println("Analysis failed: " + exception.getMessage());
            System.exit(1);
        }
    }
}
