package com.xenoamess.vivhite_video_framework.maker;

import java.nio.file.Path;

public final class DirectorMain {
    private DirectorMain() { }

    public static void main(String[] args) {
        try {
            if ((args.length == 4 || args.length == 5) && args[0].equals("produce")) {
                VideoProduction.produce(Path.of(args[1]), Path.of(args[2]), Path.of(args[3]),
                        args.length == 5 ? args[4] : VideoProduction.executable("MAKER_PYTHON", "python"));
            } else if (args.length == 4 && args[0].equals("preview")) {
                VideoProduction.preview(Path.of(args[1]), Path.of(args[2]), Path.of(args[3]));
            } else if (args.length == 2 && args[0].equals("validate-production")) {
                ProductionPlan.load(Path.of(args[1]));
                System.out.println("Production plan is valid");
            } else if (args.length == 4 && args[0].equals("render")) {
                DirectorScript.render(Path.of(args[1]), Path.of(args[2]), Path.of(args[3]));
            } else if (args.length == 3 && args[0].equals("prepare")) {
                DirectorPlanner.prepare(Path.of(args[1]), Path.of(args[2]));
            } else if (args.length == 3 && args[0].equals("generate")) {
                DirectorPlanner.generate(Path.of(args[1]), Path.of(args[2]));
            } else {
                throw new IllegalArgumentException("Usage: prepare ANALYSIS.json OUT_DIR | generate ANALYSIS.json OUT_DIR | "
                        + "render ANALYSIS.json DIRECTOR.json OUT_DIR | validate-production PLAN.json | "
                        + "preview PLAN.json OUT_DIR PRESENTER | produce PLAN.json OUT_DIR PRESENTER [PYTHON]");
            }
        } catch (Exception exception) {
            System.err.println("Video maker failed: " + exception.getMessage());
            System.exit(1);
        }
    }
}
