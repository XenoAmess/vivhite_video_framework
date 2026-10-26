package com.xenoamess.vivhite_video_framework.maker;

import com.fasterxml.jackson.databind.JsonNode;
import java.awt.AlphaComposite;
import java.awt.BasicStroke;
import java.awt.Color;
import java.awt.Font;
import java.awt.Graphics2D;
import java.awt.RenderingHints;
import java.awt.geom.Line2D;
import java.awt.geom.Path2D;
import java.awt.geom.RoundRectangle2D;
import java.awt.image.BufferedImage;
import java.util.ArrayList;
import java.util.Arrays;
import java.util.List;
import java.util.Random;

/** Deterministic mathematical animation primitives on a 1280 x 720 stage. */
final class MathCanvas {
    private static final Color PAPER = new Color(247, 243, 232);
    private static final Color INK = new Color(47, 54, 68);
    private static final Color TEAL = new Color(28, 139, 147);
    private static final Color PURPLE = new Color(116, 83, 147);
    private static final Color PINK = new Color(203, 84, 126);
    private static final Color ORANGE = new Color(222, 142, 66);
    private static final Color[] COLORS = {TEAL, PINK, PURPLE, new Color(59, 124, 171), ORANGE, new Color(78, 143, 94), new Color(170, 112, 59), new Color(130, 120, 160), INK};
    private final BufferedImage image;
    private final BufferedImage background;
    private final PresenterAsset presenter;
    private final String font;
    private Graphics2D g;
    private JsonNode activeTiming;
    private double activeSeconds;

    MathCanvas(int width, int height, PresenterAsset presenter, String font) {
        this.image = new BufferedImage(width, height, BufferedImage.TYPE_3BYTE_BGR);
        this.background = new BufferedImage(width, height, BufferedImage.TYPE_3BYTE_BGR);
        this.presenter = presenter;
        this.font = font;
        Graphics2D bg = background.createGraphics();
        bg.setColor(PAPER);
        bg.fillRect(0, 0, width, height);
        Random random = new Random(42);
        for (int i = 0; i < width * height / 10; i++) {
            int shade = random.nextInt(18) + 225;
            bg.setColor(new Color(shade, shade - 3, shade - 8, 40));
            bg.fillRect(random.nextInt(width), random.nextInt(height), 1, 1);
        }
        bg.dispose();
    }

    BufferedImage render(JsonNode beat, JsonNode timing, double seconds, double globalSeconds, int index, int count) {
        g = image.createGraphics();
        activeTiming = timing;
        activeSeconds = seconds;
        try {
            g.drawImage(background, 0, 0, null);
            g.scale(image.getWidth() / 1280.0, image.getHeight() / 720.0);
            g.setRenderingHint(RenderingHints.KEY_ANTIALIASING, RenderingHints.VALUE_ANTIALIAS_ON);
            g.setRenderingHint(RenderingHints.KEY_TEXT_ANTIALIASING, RenderingHints.VALUE_TEXT_ANTIALIAS_ON);
            g.setRenderingHint(RenderingHints.KEY_INTERPOLATION, RenderingHints.VALUE_INTERPOLATION_BICUBIC);
            double duration = timing.path("frames").asDouble() / timing.path("fps").asInt(30);
            double progress = Math.max(0, Math.min(1, (seconds - 0.25) / Math.max(1, duration - 1.2)));
            box(48, 27, 360, 36, PURPLE);
            text(beat.path("chapter").asText(), 65, 53, 23, Color.WHITE, true, 330);
            text("滑块拼图 · 奇偶实验室", 976, 53, 19, PURPLE, false, 260);
            text(beat.path("heading").asText(), 66, 127, 42, INK, true, 1120);
            g.setColor(new Color(192, 180, 155));
            g.drawLine(66, 150, 1215, 150);
            for (int i = 0; i < count; i++) {
                g.setColor(i < index ? TEAL : new Color(218, 211, 194));
                g.fillRect(65 + i * 1150 / count, 688, Math.max(2, 1150 / count - 2), 3);
            }
            String view = beat.path("view").asText();
            switch (view) {
                case "board", "route" -> boards(beat, progress, seconds, view.equals("route"));
                case "wires", "swap" -> wires(beat, progress);
                case "parity" -> parity(beat, progress);
                case "cycle" -> cycles(beat, progress);
                case "search" -> search(beat, progress);
                case "credits" -> credits(beat, progress);
                default -> throw new IllegalArgumentException("Unknown view: " + view);
            }
            if (!beat.path("formula").asText().isBlank()) {
                box(84, 548, 940, 53, new Color(228, 236, 213));
                center(beat.path("formula").asText(), 554, 585, 29, new Color(62, 100, 70), true, 900);
            }
            text(beat.path("note").asText(), 86, 626, 18, new Color(114, 113, 108), false, 940);
            presenter(beat.path("reaction").asText(), seconds, globalSeconds);
            for (JsonNode caption : timing.path("captions")) {
                if (seconds >= caption.path("start").asDouble() && seconds < caption.path("end").asDouble()) {
                    String value = caption.path("text").asText();
                    g.setFont(new Font(font, Font.PLAIN, 29));
                    int width = Math.min(1160, g.getFontMetrics().stringWidth(value) + 42);
                    box((1280 - width) / 2.0, 641, width, 43, new Color(36, 41, 46, 225));
                    center(value, 640, 673, 29, Color.WHITE, false, width - 28);
                    break;
                }
            }
        } finally { g.dispose(); }
        return image;
    }

    private record Motion(int[] before, int[] after, int index, double fraction) { }

    private Motion motion(JsonNode beat, double progress) {
        JsonNode states = beat.path("states");
        int size = states.size();
        JsonNode times = activeTiming.path("moveTimes");
        if (times.isArray() && !times.isEmpty()) {
            int index = 0;
            for (int i = 0; i < times.size(); i++) {
                double start = times.get(i).asDouble();
                if (activeSeconds < start) { break; }
                if (activeSeconds < start + 0.75) {
                    return new Motion(ProductionPlan.ints(states.get(i)), ProductionPlan.ints(states.get(i + 1)),
                            i, ease((activeSeconds - start) / 0.75));
                }
                index = i + 1;
            }
            int[] held = ProductionPlan.ints(states.get(index));
            return new Motion(held, held, index, 0);
        }
        double position = progress * Math.max(1, size - 1);
        int index = Math.min(size - 1, (int) position);
        int next = Math.min(size - 1, index + 1);
        // Hold each result briefly; all values displayed below use the same settled state.
        double fraction = ease(Math.min(1, (position - index) / 0.68));
        return new Motion(ProductionPlan.ints(states.get(index)), ProductionPlan.ints(states.get(next)), index, fraction);
    }

    private void boards(JsonNode beat, double p, double seconds, boolean route) {
        Motion m = motion(beat, p);
        int columns = beat.path("columns").asInt(3);
        int rows = m.before.length / columns;
        double cell = rows > 2 ? 92 : 112;
        tag(150, 195, route ? "合法滑动 · 路径回放" : beat.path("label").asText("当前棋盘"));
        drawBoard(m.before, m.after, m.fraction, columns, 150, 223, cell, beat.path("checker").asBoolean(), 1);
        if (beat.has("goal")) {
            int[] goal = ProductionPlan.ints(beat.get("goal"));
            tag(676, 195, "目标棋盘");
            drawBoard(goal, goal, 0, columns, 676, 237, rows > 2 ? 72 : 86, false, 1);
            arrow(537, 335, 638, 335, TEAL, p);
        } else {
            List<String> lines = new ArrayList<>();
            beat.path("labels").forEach(item -> lines.add(item.asText()));
            for (int i = 0; i < lines.size(); i++) {
                if (p >= i / (double) Math.max(1, lines.size()) * 0.65) {
                    text(lines.get(i), 630, 275 + i * 58, 31, i == lines.size() - 1 ? TEAL : INK, false, 390);
                }
            }
        }
        if (route) {
            int step = m.index + (m.fraction >= 0.999 && m.index < beat.path("states").size() - 1 ? 1 : 0);
            int offset = beat.path("pathOffset").asInt(0);
            int total = beat.path("totalSteps").asInt(beat.path("states").size() - 1);
            text("第 " + (step + offset) + " / " + total + " 步", 160, 510, 28, TEAL, true, 430);
            int[] state = m.fraction >= 0.999 ? m.after : m.before;
            text("标记 I = " + PuzzleMath.signature(state, columns), 680, 492, 28, TEAL, true, 320);
        }
    }

    private void drawBoard(int[] before, int[] after, double p, int cols, double x, double y, double cell,
                           boolean checker, double alpha) {
        g.setComposite(AlphaComposite.SrcOver.derive((float) alpha));
        int rows = before.length / cols;
        box(x - 10, y - 10, cols * cell + 20, rows * cell + 20, new Color(221, 213, 194));
        for (int i = 0; i < before.length; i++) {
            Color color = checker && (i / cols + i % cols) % 2 == 1 ? new Color(203, 221, 219) : new Color(237, 234, 219);
            box(x + (i % cols) * cell + 3, y + (i / cols) * cell + 3, cell - 6, cell - 6, color);
        }
        for (int i = 0; i < before.length; i++) {
            int value = before[i];
            int target = indexOf(after, value);
            double tx = x + ((i % cols) * (1 - p) + (target % cols) * p) * cell;
            double ty = y + ((i / cols) * (1 - p) + (target / cols) * p) * cell;
            if (value == 0) {
                g.setColor(TEAL);
                g.setStroke(new BasicStroke(2, BasicStroke.CAP_ROUND, BasicStroke.JOIN_ROUND, 1, new float[]{5, 5}, 0));
                g.draw(new RoundRectangle2D.Double(tx + 9, ty + 9, cell - 18, cell - 18, 16, 16));
                center("0", tx + cell / 2, ty + cell * 0.64, (int) (cell * 0.35), TEAL, false, (int) cell);
            } else {
                box(tx + 4, ty + 7, cell - 8, cell - 8, new Color(195, 185, 162));
                box(tx + 4, ty + 3, cell - 8, cell - 8, Color.WHITE);
                center(String.valueOf(value), tx + cell / 2, ty + cell * 0.66, (int) (cell * 0.48), COLORS[value % COLORS.length], true, (int) cell - 12);
            }
        }
        g.setComposite(AlphaComposite.SrcOver);
        g.setStroke(new BasicStroke(2));
    }

    private void wires(JsonNode beat, double p) {
        Motion m = motion(beat, p);
        int[] current = m.fraction >= 0.999 ? m.after : m.before;
        int n = current.length;
        double[] position = new double[n];
        double left = 180;
        double spacing = 780.0 / (n - 1);
        boolean swap = beat.path("view").asText().equals("swap");
        for (int value = 0; value < n; value++) {
            position[value] = indexOf(m.before, value) * (1 - m.fraction) + indexOf(m.after, value) * m.fraction;
        }
        tag(85, 200, swap ? "抽象对换 · 不代表合法滑动" : "棋盘按行展开（包含空格 0）");
        text("排序参照 0 → " + (n - 1), 85, 518, 21, INK, false, 380);
        double reveal = beat.path("reveal").asBoolean() ? ease(Math.min(1, p * 1.8)) : 1;
        for (int value = 0; value < n; value++) {
            Color color = COLORS[value % COLORS.length];
            double startX = left + position[value] * spacing;
            double endX = left + value * spacing;
            g.setColor(color);
            g.setStroke(new BasicStroke(value == 0 ? 2.5f : 3.2f));
            g.draw(new Line2D.Double(startX, 263, startX + (endX - startX) * reveal, 263 + 187 * reveal));
            token(String.valueOf(value), startX, 245, color, value == 0);
            token(String.valueOf(value), endX, 471, color, value == 0);
        }
        int count = PuzzleMath.inversions(current);
        if (activeTiming.path("pairFocus").isArray() && !activeTiming.path("pairFocus").isEmpty()) {
            JsonNode selected = null;
            int shown = 0;
            for (JsonNode focus : activeTiming.path("pairFocus")) {
                if (activeSeconds >= focus.path("time").asDouble()) { selected = focus; shown++; }
            }
            if (selected != null) {
                int a = selected.path("pair").get(0).asInt();
                int b = selected.path("pair").get(1).asInt();
                for (int value : new int[]{a, b}) {
                    g.setColor(PINK);
                    g.setStroke(new BasicStroke(6));
                    g.draw(new Line2D.Double(left + position[value] * spacing, 263, left + value * spacing, 450));
                }
                boolean crosses = (position[a] - position[b]) * (a - b) < 0;
                String annotation = beat.path("countPairs").asBoolean()
                        ? "第 " + shown + " 对：" + a + " 与 " + b
                        : a + " 与 " + b + (crosses ? "：有交叉" : "：不交叉");
                text(annotation, 720, 518, 23, PINK, true, 310);
            }
        } else if (beat.path("countPairs").asBoolean()) {
            var pairs = new ArrayList<int[]>();
            for (int i = 0; i < current.length; i++) {
                for (int j = i + 1; j < current.length; j++) {
                    if (current[i] > current[j]) { pairs.add(new int[]{current[i], current[j]}); }
                }
            }
            int show = Math.min(pairs.size(), 1 + (int) (p * pairs.size()));
            if (!pairs.isEmpty()) {
                int[] active = pairs.get(Math.max(0, show - 1));
                for (int value : active) {
                    g.setColor(PINK);
                    g.setStroke(new BasicStroke(6));
                    g.draw(new Line2D.Double(left + position[value] * spacing, 263, left + value * spacing, 450));
                }
                text("第 " + show + " 对：" + active[0] + " 与 " + active[1], 750, 518, 23, PINK, true, 280);
            }
        } else {
            text("交叉线对数 τ = " + count + "   " + ((count & 1) == 0 ? "偶" : "奇"), 690, 518, 24, PINK, true, 340);
        }
    }

    private void parity(JsonNode beat, double p) {
        Motion m = motion(beat, p);
        int cols = beat.path("columns").asInt(3);
        int[] current = m.fraction >= 0.999 ? m.after : m.before;
        tag(90, 200, "同一次滑动，观察两个读数");
        drawBoard(m.before, m.after, m.fraction, cols, 104, 246, 86, true, 1);
        int inversion = PuzzleMath.inversions(current);
        int zero = PuzzleMath.blank(current);
        int color = (zero / cols + zero % cols) & 1;
        text("交叉奇偶", 520, 252, 25, PINK, false, 280);
        pill(770, 213, inversion & 1, PINK);
        text("τ = " + inversion, 890, 251, 26, PINK, true, 140);
        text("空格颜色", 520, 335, 25, TEAL, false, 280);
        pill(770, 295, color, TEAL);
        text("r+c = " + (zero / cols + zero % cols), 880, 334, 24, TEAL, true, 160);
        g.setStroke(new BasicStroke(2));
        g.setColor(new Color(178, 173, 158));
        g.drawLine(520, 375, 1000, 375);
        text("合成标记", 520, 434, 28, INK, true, 250);
        pill(770, 394, PuzzleMath.signature(current, cols), PURPLE);
        text("始终相同", 880, 434, 26, PURPLE, true, 150);
        text("r、c 从 0 开始；0 也参与逆序计数", 103, 511, 21, INK, false, 700);
    }

    private void cycles(JsonNode beat, double p) {
        Motion m = motion(beat, p);
        tag(80, 197, "四格棋盘 → 沿外圈读取顺序");
        drawBoard(m.before, m.after, m.fraction, 2, 100, 260, 90, false, 1);
        arrow(312, 350, 405, 350, TEAL, p);
        boolean components = beat.path("components").asBoolean();
        if (components) {
            for (int group = 0; group < 2; group++) {
                int[] root = group == 0 ? new int[]{1, 2, 3, 0} : new int[]{2, 1, 3, 0};
                List<int[]> cycle = cycleStates(root);
                double cx = group == 0 ? 567 : 872;
                double cy = 352;
                g.setColor(group == 0 ? TEAL : PINK);
                g.setStroke(new BasicStroke(2));
                g.drawOval((int) cx - 100, (int) cy - 100, 200, 200);
                int active = Math.min(11, (int) (p * 12));
                for (int i = 0; i < 12; i++) {
                    double angle = -Math.PI / 2 + i * Math.PI / 6;
                    double x = cx + Math.cos(angle) * 100;
                    double y = cy + Math.sin(angle) * 100;
                    g.setColor(i == active && group == 0 ? ORANGE : group == 0 ? TEAL : PINK);
                    g.fillOval((int) x - 6, (int) y - 6, 12, 12);
                    if (i == active) {
                        int[] state = cycle.get(i);
                        drawBoard(state, state, 0, 2, cx - 44, cy - 44, 44, false, 1);
                    }
                }
                center("12 个局面", cx, 499, 25, group == 0 ? TEAL : PINK, true, 240);
            }
        } else {
            int[] current = m.fraction >= 0.999 ? m.after : m.before;
            int[] order = {0, 1, 3, 2};
            double cx = 710;
            double cy = 350;
            g.setColor(new Color(201, 191, 171));
            g.setStroke(new BasicStroke(3));
            g.drawOval(590, 230, 240, 240);
            for (int i = 0; i < 4; i++) {
                double angle = -Math.PI / 2 + i * Math.PI / 2;
                token(String.valueOf(current[order[i]]), cx + Math.cos(angle) * 120, cy + Math.sin(angle) * 120,
                        current[order[i]] == 0 ? TEAL : COLORS[current[order[i]]], current[order[i]] == 0);
            }
            center("忽略空格后：循环次序不变", 710, 518, 26, TEAL, true, 560);
        }
    }

    static List<int[]> cycleStates(int[] root) {
        var states = new ArrayList<int[]>();
        int[] previous = null;
        int[] current = root;
        do {
            states.add(current);
            List<int[]> neighbors = PuzzleMath.neighbors(current, 2);
            int[] next = neighbors.getFirst();
            if (previous != null && Arrays.equals(previous, next)) { next = neighbors.getLast(); }
            previous = current;
            current = next;
        } while (!Arrays.equals(current, root));
        return states;
    }

    private void search(JsonNode beat, double p) {
        int[] root = ProductionPlan.ints(beat.path("states").get(0));
        var layers = new ArrayList<List<int[]>>();
        var seen = new java.util.HashSet<String>();
        layers.add(List.of(root));
        seen.add(Arrays.toString(root));
        for (int depth = 1; depth <= 3; depth++) {
            var layer = new ArrayList<int[]>();
            for (int[] state : layers.get(depth - 1)) {
                for (int[] next : PuzzleMath.neighbors(state, 3)) {
                    if (seen.add(Arrays.toString(next))) { layer.add(next); }
                }
            }
            layers.add(layer);
        }
        int total = layers.stream().mapToInt(List::size).sum();
        int reveal = Math.max(1, (int) (p * (total + 2)));
        int ordinal = 0;
        tag(84, 198, "一个节点 = 一个局面；一条边 = 一次合法滑动");
        for (int depth = 0; depth < layers.size(); depth++) {
            List<int[]> layer = layers.get(depth);
            for (int i = 0; i < layer.size(); i++) {
                if (ordinal++ > reveal) { continue; }
                double x = 220 + depth * 240;
                double y = 242 + (i + 0.5) * 270 / layer.size();
                int[] state = layer.get(i);
                if (depth > 0) {
                    List<int[]> previous = layers.get(depth - 1);
                    for (int j = 0; j < previous.size(); j++) {
                        if (PuzzleMath.legalMove(previous.get(j), state, 3)) {
                            g.setColor(new Color(170, 186, 179));
                            g.setStroke(new BasicStroke(2));
                            g.draw(new Line2D.Double(x - 188, 242 + (j + 0.5) * 270 / previous.size(), x - 52, y));
                        }
                    }
                }
                drawBoard(state, state, 0, 3, x - 48, y - 32, 32, false, 1);
            }
            center("深度 " + depth, 220 + depth * 240, 528, 22, TEAL, true, 160);
        }
    }

    private void credits(JsonNode beat, double p) {
        List<String> lines = new ArrayList<>();
        beat.path("labels").forEach(line -> lines.add(line.asText()));
        for (int i = 0; i < lines.size(); i++) {
            text(lines.get(i), 110, 238 + i * 51, i == 0 ? 33 : 24, i == 0 ? TEAL : INK, i == 0, 910);
        }
        arrow(110, 510, 1000, 510, TEAL, p);
    }

    private void presenter(String reaction, double localSeconds, double globalSeconds) {
        double enter = ease(Math.min(1, localSeconds * 2));
        double x = 1082 + (1 - enter) * 180;
        double y = 425 + Math.sin(localSeconds * 1.6) * 3;
        if (!reaction.isBlank()) {
            box(x - 25, 315, 177, 84, Color.WHITE);
            wrap(reaction, x - 10, 346, 22, 145, PURPLE, 2);
            arrow(x + 40, 399, x + 62, 416, PURPLE, 1);
        }
        BufferedImage avatar = presenter.frame(globalSeconds);
        box(x - 5, y - 5, 150, 174, Color.WHITE);
        double scale = Math.min(140.0 / avatar.getWidth(), 140.0 / avatar.getHeight());
        g.drawImage(avatar, (int) (x + (140 - avatar.getWidth() * scale) / 2), (int) y,
                (int) (avatar.getWidth() * scale), (int) (avatar.getHeight() * scale), null);
        center(presenter.isStill() ? "形象占位" : "视频形象", x + 70, y + 161, 16, PURPLE, false, 140);
        // The pointer belongs to the presenter layer, so a later video asset keeps the teaching cue.
        if (!reaction.isBlank()) { arrow(x - 10, y + 90, 1023, y + 64, PURPLE, 1); }
    }

    private void wrap(String value, double x, double y, int size, int width, Color color, int maxLines) {
        StringBuilder line = new StringBuilder();
        int row = 0;
        g.setFont(new Font(font, Font.PLAIN, size));
        for (char character : value.toCharArray()) {
            if (g.getFontMetrics().stringWidth(line.toString() + character) > width) {
                text(line.toString(), x, y + row++ * (size + 8), size, color, false, width);
                line.setLength(0);
                if (row >= maxLines) { return; }
            }
            line.append(character);
        }
        text(line.toString(), x, y + row * (size + 8), size, color, false, width);
    }

    private void tag(double x, double y, String value) {
        text(value, x, y, 22, new Color(138, 107, 69), true, 920);
    }

    private void pill(double x, double y, int value, Color color) {
        box(x, y, 76, 57, color);
        center(String.valueOf(value), x + 38, y + 43, 36, Color.WHITE, true, 66);
    }

    private void token(String value, double x, double y, Color color, boolean blank) {
        g.setColor(blank ? new Color(220, 237, 232) : Color.WHITE);
        g.fillOval((int) x - 22, (int) y - 22, 44, 44);
        g.setColor(color);
        g.setStroke(new BasicStroke(2));
        g.drawOval((int) x - 22, (int) y - 22, 44, 44);
        center(value, x, y + 9, 26, color, true, 40);
    }

    private void box(double x, double y, double width, double height, Color color) {
        g.setColor(color);
        g.fill(new RoundRectangle2D.Double(x, y, width, height, 11, 11));
    }

    private void arrow(double x1, double y1, double x2, double y2, Color color, double progress) {
        double x = x1 + (x2 - x1) * Math.min(1, progress * 2);
        double y = y1 + (y2 - y1) * Math.min(1, progress * 2);
        g.setColor(color);
        g.setStroke(new BasicStroke(3));
        g.draw(new Line2D.Double(x1, y1, x, y));
        double a = Math.atan2(y2 - y1, x2 - x1);
        Path2D path = new Path2D.Double();
        path.moveTo(x, y);
        path.lineTo(x - 13 * Math.cos(a - 0.4), y - 13 * Math.sin(a - 0.4));
        path.lineTo(x - 13 * Math.cos(a + 0.4), y - 13 * Math.sin(a + 0.4));
        path.closePath();
        g.fill(path);
    }

    private void center(String value, double x, double y, int size, Color color, boolean bold, int maxWidth) {
        fit(value, size, bold, maxWidth);
        g.setColor(color);
        g.drawString(value, (float) (x - g.getFontMetrics().stringWidth(value) / 2.0), (float) y);
    }

    private void text(String value, double x, double y, int size, Color color, boolean bold, int maxWidth) {
        fit(value, size, bold, maxWidth);
        g.setColor(color);
        g.drawString(value, (float) x, (float) y);
    }

    private void fit(String value, int size, boolean bold, int width) {
        do { g.setFont(new Font(font, bold ? Font.BOLD : Font.PLAIN, size--)); }
        while (g.getFontMetrics().stringWidth(value) > width && size > 11);
    }

    private static int indexOf(int[] values, int value) {
        for (int i = 0; i < values.length; i++) { if (values[i] == value) { return i; } }
        throw new IllegalArgumentException("Missing tile identity");
    }

    private static double ease(double value) { return value * value * (3 - 2 * value); }
}
