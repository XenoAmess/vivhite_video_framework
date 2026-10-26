package com.xenoamess.vivhite_video_framework.maker;

import java.awt.image.BufferedImage;
import java.io.IOException;
import java.nio.file.Files;
import java.nio.file.Path;
import java.time.Duration;
import java.util.ArrayList;
import java.util.List;
import java.util.Locale;
import javax.imageio.ImageIO;

/** A still today, or a loop of externally rendered Live2D/video frames later. */
final class PresenterAsset {
    private final List<BufferedImage> frames;

    private PresenterAsset(List<BufferedImage> frames) { this.frames = List.copyOf(frames); }

    static PresenterAsset open(Path source, Path output, String ffmpeg) throws Exception {
        String name = source.getFileName().toString().toLowerCase(Locale.ROOT);
        var frames = new ArrayList<BufferedImage>();
        if (name.endsWith(".png") || name.endsWith(".jpg") || name.endsWith(".jpeg")) {
            BufferedImage image = ImageIO.read(source.toFile());
            if (image == null) { throw new IOException("Unsupported presenter image: " + source); }
            frames.add(image);
        } else if (name.endsWith(".mp4") || name.endsWith(".webm") || name.endsWith(".mov")) {
            Path directory = output.resolve("presenter-" + DirectorScript.fingerprint(source).substring(0, 16));
            Files.createDirectories(directory);
            MediaProcess.run(List.of(ffmpeg, "-v", "error", "-y", "-i", source.toString(), "-t", "120",
                    "-vf", "fps=12,scale=192:192:force_original_aspect_ratio=decrease", "-frames:v", "1440",
                    directory.resolve("%05d.png").toString()), Duration.ofMinutes(3));
            try (var paths = Files.list(directory)) {
                for (Path path : paths.filter(p -> p.toString().endsWith(".png")).sorted().toList()) {
                    frames.add(ImageIO.read(path.toFile()));
                }
            }
            if (frames.isEmpty() || frames.contains(null)) { throw new IOException("No valid presenter video frames"); }
        } else {
            throw new IllegalArgumentException("Presenter must be PNG/JPEG, MP4, MOV or WebM");
        }
        return new PresenterAsset(frames);
    }

    BufferedImage frame(double seconds) { return frames.get((int) (seconds * 12) % frames.size()); }
    boolean isStill() { return frames.size() == 1; }
}
