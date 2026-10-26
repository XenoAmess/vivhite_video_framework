package com.xenoamess.vivhite_video_framework.maker;

import java.awt.Font;
import java.awt.Graphics2D;
import java.awt.font.FontRenderContext;
import java.awt.font.TextAttribute;
import java.awt.font.TextLayout;
import java.text.AttributedString;
import java.util.Collections;
import java.util.LinkedHashMap;
import java.util.List;
import java.util.Map;

/** Cached glyph-aware typography: keep Chinese text while supplying missing mathematical symbols. */
final class MathText {
    private record Key(String value, Font font, FontRenderContext context) { }
    private static final List<String> FALLBACKS = List.of("Cambria Math", "Segoe UI Symbol", "Arial Unicode MS", "Dialog");
    private static final Map<Key, TextLayout> LAYOUTS = Collections.synchronizedMap(new LinkedHashMap<>(256, 0.75f, true) {
        @Override protected boolean removeEldestEntry(Map.Entry<Key, TextLayout> eldest) { return size() > 4096; }
    });

    private MathText() { }

    static int width(Graphics2D graphics, String value) {
        return value.isEmpty() ? 0 : (int) Math.ceil(layout(graphics, value).getAdvance());
    }

    static void draw(Graphics2D graphics, String value, double x, double y) {
        if (!value.isEmpty()) { layout(graphics, value).draw(graphics, (float) x, (float) y); }
    }

    private static TextLayout layout(Graphics2D graphics, String value) {
        Font primary = graphics.getFont();
        Key key = new Key(value, primary, graphics.getFontRenderContext());
        return LAYOUTS.computeIfAbsent(key, unused -> {
            if (primary.canDisplayUpTo(value) < 0) { return new TextLayout(value, primary, key.context()); }
            AttributedString attributed = new AttributedString(value);
            attributed.addAttribute(TextAttribute.FONT, primary);
            for (int offset = 0; offset < value.length();) {
                int code = value.codePointAt(offset);
                int count = Character.charCount(code);
                if (!primary.canDisplay(code)) {
                    Font selected = null;
                    for (String family : FALLBACKS) {
                        Font candidate = new Font(family, primary.getStyle(), primary.getSize());
                        if (candidate.canDisplay(code)) { selected = candidate; break; }
                    }
                    ProductionPlan.require(selected != null, "No installed font can display mathematical symbol U+"
                            + Integer.toHexString(code).toUpperCase(java.util.Locale.ROOT));
                    attributed.addAttribute(TextAttribute.FONT, selected, offset, offset + count);
                }
                offset += count;
            }
            return new TextLayout(attributed.getIterator(), key.context());
        });
    }
}
