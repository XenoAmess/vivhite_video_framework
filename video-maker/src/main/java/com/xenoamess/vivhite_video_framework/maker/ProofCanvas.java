package com.xenoamess.vivhite_video_framework.maker;

import com.fasterxml.jackson.databind.JsonNode;
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
import java.util.HashMap;
import java.util.IdentityHashMap;
import java.util.List;
import java.util.Map;

/** Reusable proof stage: cached diagrams and text, with actual moving token identities. */
final class ProofCanvas {
    private static final Color INK = new Color(47, 54, 68);
    private static final Color TEAL = new Color(28, 139, 147);
    private static final Color PURPLE = new Color(116, 83, 147);
    private static final Color PINK = new Color(203, 84, 126);
    private static final Color[] COLORS = {TEAL, PINK, PURPLE, new Color(59, 124, 171),
            new Color(222, 142, 66), new Color(78, 143, 94), new Color(170, 112, 59)};
    private final String family;
    private final Map<Integer, Font> fonts = new HashMap<>();
    private final Map<JsonNode, ProofScene> scenes = new IdentityHashMap<>();
    private final BufferedImage base;
    private ProofScene cachedScene;
    private int cachedStep = -1;

    ProofCanvas(String family, int width, int height) {
        this.family = family;
        this.base = new BufferedImage(width, height, BufferedImage.TYPE_INT_ARGB);
    }

    void render(Graphics2D destination, JsonNode beat, JsonNode timing, double seconds, double progress) {
        ProofScene scene = scenes.computeIfAbsent(beat, key -> ProofScene.parse(key.path("proof"), key.path("narration").asText()));
        ProofScene.Frame frame = scene.frame(timing, seconds, progress);
        if (cachedScene != scene || cachedStep != frame.index()) {
            prepare(scene, frame);
            cachedScene = scene;
            cachedStep = frame.index();
        }
        destination.drawImage(base, 0, 0, 1280, 720, null);
        drawTokens(destination, scene, frame);
    }

    private void prepare(ProofScene scene, ProofScene.Frame frame) {
        Graphics2D g = base.createGraphics();
        try {
            g.setComposite(java.awt.AlphaComposite.Clear);
            g.fillRect(0, 0, base.getWidth(), base.getHeight());
            g.setComposite(java.awt.AlphaComposite.SrcOver);
            g.scale(base.getWidth() / 1280.0, base.getHeight() / 720.0);
            g.setRenderingHint(RenderingHints.KEY_ANTIALIASING, RenderingHints.VALUE_ANTIALIAS_ON);
            g.setRenderingHint(RenderingHints.KEY_TEXT_ANTIALIASING, RenderingHints.VALUE_TEXT_ANTIALIAS_ON);
            ProofScene.Step step = frame.step();
            g.setFont(font(23, true));
            g.setColor(PURPLE);
            String heading = (frame.index() + 1) + "/" + scene.steps.size() + "  " + step.text();
            List<String> title = wrap(g, heading, 940);
            ProductionPlan.require(title.size() <= 2, "Proof step heading overflow; shorten text");
            for (int i = 0; i < title.size(); i++) { MathText.draw(g, title.get(i), 85, 184 + i * 27); }
            for (ProofScene.Edge edge : step.edges()) {
                double[] a = point(scene, edge.a());
                double[] b = point(scene, edge.b());
                boolean focused = step.focus().contains(edge.a()) && step.focus().contains(edge.b());
                g.setColor(focused ? TEAL : new Color(170, 178, 172));
                g.setStroke(new BasicStroke(focused ? 5 : 2.5f));
                g.draw(new Line2D.Double(a[0], a[1], b[0], b[1]));
            }
            for (int i = 0; i < scene.vertices.size(); i++) {
                double[] p = point(scene, i);
                boolean focused = step.focus().contains(i);
                g.setColor(focused ? new Color(199, 229, 215) : new Color(236, 232, 217));
                g.fillOval((int) p[0] - 25, (int) p[1] - 25, 50, 50);
                if (i == scene.root) {
                    g.setColor(PURPLE);
                    g.setStroke(new BasicStroke(3));
                    g.drawOval((int) p[0] - 29, (int) p[1] - 29, 58, 58);
                }
                g.setFont(font(15, false));
                g.setColor(i == scene.root ? PURPLE : INK);
                String label = scene.vertices.get(i).label() + (i == scene.root ? " · 根" : "");
                center(g, label, p[0], p[1] + 43, 130);
            }
            for (int[] cycle : step.cycles()) {
                for (int i = 0; i < cycle.length; i++) {
                    double[] a = point(scene, cycle[i]);
                    double[] b = point(scene, cycle[(i + 1) % cycle.length]);
                    arrow(g, a[0], a[1], b[0], b[1]);
                }
            }
            if (scene.pointer && !step.focus().isEmpty()) {
                double x = 0;
                double y = 0;
                for (int node : step.focus()) {
                    double[] p = point(scene, node);
                    x += p[0];
                    y += p[1];
                }
                arrow(g, 1065, 465, x / step.focus().size(), y / step.focus().size());
            }
            drawRows(g, scene, step);
            g.setFont(font(18, true));
            g.setColor(step.algebra() ? PURPLE : TEAL);
            String layer = step.algebra() ? "代数层 · 位置置换，不表示一步合法滑动"
                    : scene.vertices.isEmpty() ? "推导层 · 按阶段展开" : "图上操作 · 空格只沿边滑动";
            MathText.draw(g, layer, 85, 536);
        } finally { g.dispose(); }
    }

    private void drawRows(Graphics2D g, ProofScene scene, ProofScene.Step step) {
        boolean diagram = !scene.vertices.isEmpty();
        int left = diagram ? 640 : 95;
        int width = diagram ? 382 : 925;
        int top = 233;
        int bottom = 517;
        int desired = diagram ? 23 : 30;
        List<List<String>> lines = List.of();
        int lineHeight = 0;
        int spacing = 0;
        int selectedSize = desired;
        for (; selectedSize >= 21; selectedSize--) {
            g.setFont(font(selectedSize, false));
            lines = new ArrayList<>();
            int totalLines = 0;
            for (String row : step.rows()) {
                List<String> parts = wrap(g, row, width - 20);
                lines.add(parts);
                totalLines += parts.size();
            }
            lineHeight = selectedSize + 5;
            spacing = 8;
            if (totalLines * lineHeight + Math.max(0, lines.size() - 1) * spacing <= bottom - top + lineHeight) { break; }
        }
        ProductionPlan.require(selectedSize >= 21, "Proof table is too dense to read; split rows into more steps");
        int baseline = top;
        for (int i = 0; i < lines.size(); i++) {
            List<String> row = lines.get(i);
            boolean highlighted = i == step.highlightRow();
            if (highlighted) {
                g.setColor(new Color(213, 235, 218));
                g.fill(new RoundRectangle2D.Double(left - 8, baseline - selectedSize - 4, width + 16,
                        row.size() * lineHeight + 6, 10, 10));
            }
            g.setColor(highlighted ? TEAL : INK);
            g.setFont(font(selectedSize, highlighted));
            for (String line : row) {
                MathText.draw(g, line, left, baseline);
                baseline += lineHeight;
            }
            baseline += spacing;
        }
    }

    private void drawTokens(Graphics2D g, ProofScene scene, ProofScene.Frame frame) {
        int[] before = frame.before();
        int[] after = frame.after();
        double fraction = frame.fraction();
        double[] xs = new double[before.length];
        double[] ys = new double[before.length];
        for (int position = 0; position < before.length; position++) {
            int identity = before[position];
            int destination = position;
            for (int j = 0; j < after.length; j++) { if (after[j] == identity) { destination = j; break; } }
            double[] from = point(scene, position);
            double[] to = point(scene, destination);
            double x = from[0] + (to[0] - from[0]) * fraction;
            double y = from[1] + (to[1] - from[1]) * fraction;
            if (frame.step().algebra() && position != destination) {
                double length = Math.hypot(to[0] - from[0], to[1] - from[1]);
                double arc = Math.sin(Math.PI * fraction) * 16;
                x -= (to[1] - from[1]) / length * arc;
                y += (to[0] - from[0]) / length * arc;
            }
            xs[identity] = x;
            ys[identity] = y;
        }
        // Blank is drawn first, so a moving numbered tile stays legible during an adjacent swap.
        for (int pass = 0; pass < 2; pass++) {
            for (int identity = 0; identity < scene.tokenLabels.length; identity++) {
                boolean blank = scene.blankIdentity == identity;
                if ((pass == 0) != blank) { continue; }
                double x = xs[identity];
                double y = ys[identity];
                Color color = COLORS[identity % COLORS.length];
                g.setColor(blank ? new Color(218, 237, 230) : Color.WHITE);
                g.fillOval((int) x - 20, (int) y - 20, 40, 40);
                g.setColor(blank ? TEAL : color);
                g.setStroke(blank ? new BasicStroke(2, BasicStroke.CAP_ROUND, BasicStroke.JOIN_ROUND, 1, new float[]{4, 4}, 0)
                        : new BasicStroke(2));
                g.drawOval((int) x - 20, (int) y - 20, 40, 40);
                int size = 23;
                do { g.setFont(font(size--, true)); }
                while (MathText.width(g, scene.tokenLabels[identity]) > 37 && size >= 13);
                ProductionPlan.require(MathText.width(g, scene.tokenLabels[identity]) <= 37,
                        "Proof token label is too long to fit; use a short label and explain it in rows");
                center(g, scene.tokenLabels[identity], x, y + 8, 100);
            }
        }
        g.setStroke(new BasicStroke(2));
    }

    private static double[] point(ProofScene scene, int index) {
        ProofScene.Vertex vertex = scene.vertices.get(index);
        double width = scene.hasRows ? 485 : 880;
        return new double[]{110 + vertex.x() * width, 245 + vertex.y() * 225};
    }

    private static List<String> wrap(Graphics2D graphics, String value, int width) {
        var result = new ArrayList<String>();
        StringBuilder line = new StringBuilder();
        for (int offset = 0; offset < value.length();) {
            int code = value.codePointAt(offset);
            String character = new String(Character.toChars(code));
            if (!line.isEmpty() && MathText.width(graphics, line + character) > width) {
                result.add(line.toString());
                line.setLength(0);
            }
            line.append(character);
            offset += Character.charCount(code);
        }
        if (!line.isEmpty()) { result.add(line.toString()); }
        return result;
    }

    private static void center(Graphics2D g, String label, double x, double y, int width) {
        ProductionPlan.require(MathText.width(g, label) <= width, "Proof node label is too wide");
        MathText.draw(g, label, x - MathText.width(g, label) / 2.0, y);
    }

    private static void arrow(Graphics2D g, double x1, double y1, double x2, double y2) {
        double length = Math.hypot(x2 - x1, y2 - y1);
        double dx = (x2 - x1) / length;
        double dy = (y2 - y1) / length;
        double sx = x1 + dx * 29;
        double sy = y1 + dy * 29;
        double ex = x2 - dx * 29;
        double ey = y2 - dy * 29;
        g.setColor(PURPLE);
        g.setStroke(new BasicStroke(2, BasicStroke.CAP_ROUND, BasicStroke.JOIN_ROUND, 1, new float[]{5, 4}, 0));
        g.draw(new Line2D.Double(sx, sy, ex, ey));
        Path2D head = new Path2D.Double();
        head.moveTo(ex, ey);
        head.lineTo(ex - dx * 11 - dy * 5, ey - dy * 11 + dx * 5);
        head.lineTo(ex - dx * 11 + dy * 5, ey - dy * 11 - dx * 5);
        head.closePath();
        g.fill(head);
    }

    private Font font(int size, boolean bold) {
        return fonts.computeIfAbsent(size * 2 + (bold ? 1 : 0), key -> new Font(family, bold ? Font.BOLD : Font.PLAIN, size));
    }
}
