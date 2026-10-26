package com.xenoamess.vivhite_video_framework.maker;

import com.fasterxml.jackson.databind.JsonNode;
import java.util.ArrayList;
import java.util.HashSet;
import java.util.LinkedHashMap;
import java.util.LinkedHashSet;
import java.util.List;
import java.util.Map;
import java.util.Set;

/** Validated, precomputed proof actions. A graph walk always swaps the unique blank and a neighbor. */
final class ProofScene {
    record Vertex(String id, String label, double x, double y) { }
    record Edge(int a, int b) {
        Edge { if (a > b) { int swap = a; a = b; b = swap; } }
    }
    record Step(String text, List<String> rows, int highlightRow, Set<Integer> focus,
                List<Edge> edges, List<int[]> states, boolean algebra, List<int[]> cycles) { }
    record Frame(Step step, int index, int[] before, int[] after, double fraction) { }

    final String mode;
    final List<Vertex> vertices;
    final String[] tokenLabels;
    final int root;
    final int blankIdentity;
    final List<Step> steps;
    final boolean hasRows;
    final boolean hasAlgebra;
    final boolean pointer;

    private ProofScene(String mode, List<Vertex> vertices, String[] tokenLabels, int root, int blankIdentity,
                       List<Step> steps, boolean hasRows, boolean hasAlgebra, boolean pointer) {
        this.mode = mode;
        this.vertices = List.copyOf(vertices);
        this.tokenLabels = tokenLabels;
        this.root = root;
        this.blankIdentity = blankIdentity;
        this.steps = List.copyOf(steps);
        this.hasRows = hasRows;
        this.hasAlgebra = hasAlgebra;
        this.pointer = pointer;
    }

    static ProofScene parse(JsonNode proof, String narration) {
        ProductionPlan.require(proof.isObject(), "Missing proof scene");
        String mode = ProductionPlan.text(proof, "mode");
        ProductionPlan.require(!proof.has("pointer") || proof.get("pointer").isBoolean(), "Proof pointer must be a boolean");
        ProductionPlan.require(Set.of("graph", "permutation", "table", "matrix").contains(mode), "Unsupported proof mode");
        var vertices = new ArrayList<Vertex>();
        var ids = new LinkedHashMap<String, Integer>();
        JsonNode nodes = proof.path("nodes");
        if (!nodes.isMissingNode()) { ProductionPlan.require(nodes.isArray(), "Proof nodes must be an array"); }
        ProductionPlan.require(nodes.size() <= 40, "Split proof diagrams with more than 40 nodes");
        for (JsonNode node : nodes) {
            ProductionPlan.require(node.isObject() && node.path("id").isTextual()
                    && (!node.has("label") || node.get("label").isTextual()), "Proof node IDs and labels must be strings");
            String id = ProductionPlan.text(node, "id");
            ProductionPlan.require(id.length() <= 64 && !ids.containsKey(id), "Duplicate or long proof node ID");
            String label = node.path("label").asText(id);
            ProductionPlan.require(!label.isBlank(), "Proof node label must be nonblank");
            bounded(label, 10, "Proof node label");
            double x = coordinate(node, "x");
            double y = coordinate(node, "y");
            for (Vertex previous : vertices) {
                ProductionPlan.require(previous.x() != x || previous.y() != y, "Proof nodes cannot occupy identical positions");
            }
            ids.put(id, vertices.size());
            vertices.add(new Vertex(id, label, x, y));
        }
        ProductionPlan.require(!(mode.equals("graph") || mode.equals("permutation")) || !vertices.isEmpty(),
                "Graph and permutation scenes need nodes");
        var edges = new LinkedHashSet<Edge>();
        addEdges(proof.path("edges"), ids, edges);
        int root = proof.has("root") ? nodeIndex(proof.get("root"), ids) : -1;
        int blank = proof.has("blank") ? nodeIndex(proof.get("blank"), ids) : -1;
        int blankIdentity = blank;
        String[] labels = new String[vertices.size()];
        JsonNode tokens = proof.path("initialTokens");
        if (!tokens.isMissingNode()) {
            ProductionPlan.require(tokens.isObject() && tokens.size() == vertices.size(), "initialTokens must cover every node");
            tokens.fieldNames().forEachRemaining(id -> ProductionPlan.require(ids.containsKey(id), "Unknown token position: " + id));
        }
        var labelSet = new HashSet<String>();
        for (int i = 0; i < labels.length; i++) {
            labels[i] = tokens.isMissingNode() ? (i == blank ? "0" : vertices.get(i).label())
                    : ProductionPlan.text(tokens, vertices.get(i).id());
            ProductionPlan.require(tokens.isMissingNode() || tokens.path(vertices.get(i).id()).isTextual(),
                    "Proof token labels must be strings");
            bounded(labels[i], 10, "Proof token label");
            ProductionPlan.require(labelSet.add(labels[i]), "Proof token labels must be unique");
            ProductionPlan.require(blank < 0 || labels[i].equals("0") == (i == blank), "Blank must be the unique token 0");
        }
        List<String> rows = rows(proof.path("rows"), mode);
        boolean hasRows = !rows.isEmpty();
        boolean hasAlgebra = mode.equals("permutation");
        JsonNode actions = proof.path("steps");
        ProductionPlan.require(actions.isArray() && !actions.isEmpty() && actions.size() <= 120, "Proof needs 1 to 120 action steps");
        var steps = new ArrayList<Step>();
        int[] current = new int[vertices.size()];
        for (int i = 0; i < current.length; i++) { current[i] = i; }
        for (JsonNode action : actions) {
            ProductionPlan.require(action.isObject(), "Proof step must be an object");
            ProductionPlan.require(!action.has("text") || action.get("text").isTextual(), "Proof step text must be a string");
            String text = action.path("text").asText("");
            bounded(text, 50, "Proof step text");
            if (action.has("cue")) {
                ProductionPlan.require(narration.contains(ProductionPlan.text(action, "cue")), "Proof cue is absent from narration");
            }
            if (action.has("rows")) { rows = rows(action.get("rows"), mode); }
            hasRows |= !rows.isEmpty();
            ProductionPlan.require(!action.has("highlightRow") || action.get("highlightRow").isIntegralNumber(),
                    "Proof highlightRow must be an integer");
            int highlight = action.path("highlightRow").asInt(-1);
            ProductionPlan.require(highlight >= -1 && highlight < rows.size(), "Proof highlightRow outside displayed rows");
            var focus = new LinkedHashSet<Integer>();
            if (action.has("focus")) {
                ProductionPlan.require(action.get("focus").isArray(), "Proof focus must be an array");
                for (JsonNode item : action.get("focus")) { focus.add(nodeIndex(item, ids)); }
            }
            addEdges(action.path("addEdges"), ids, edges);
            boolean walk = action.has("walk");
            boolean algebra = action.has("cycles");
            ProductionPlan.require(!(walk && algebra), "Separate legal walks and algebraic cycles into different steps");
            var states = new ArrayList<int[]>();
            var cycles = new ArrayList<int[]>();
            states.add(current.clone());
            if (walk) {
                JsonNode path = action.get("walk");
                ProductionPlan.require(blank >= 0 && path.isArray() && path.size() >= 2 && path.size() <= 500,
                        "A proof walk needs a blank and 2 to 500 path positions");
                ProductionPlan.require(nodeIndex(path.get(0), ids) == blank, "Proof walk does not start at current blank");
                for (int i = 1; i < path.size(); i++) {
                    int next = nodeIndex(path.get(i), ids);
                    ProductionPlan.require(edges.contains(new Edge(blank, next)), "Illegal proof slide: missing edge");
                    int token = current[blank];
                    current[blank] = current[next];
                    current[next] = token;
                    blank = next;
                    states.add(current.clone());
                }
            } else if (algebra) {
                JsonNode list = action.get("cycles");
                ProductionPlan.require(list.isArray() && !list.isEmpty(), "Algebraic cycles must be a nonempty array");
                var moved = new HashSet<Integer>();
                int[] before = current.clone();
                for (JsonNode cycle : list) {
                    ProductionPlan.require(cycle.isArray() && cycle.size() >= 2, "An algebraic cycle needs at least two positions");
                    int[] positions = new int[cycle.size()];
                    for (int i = 0; i < positions.length; i++) {
                        positions[i] = nodeIndex(cycle.get(i), ids);
                        ProductionPlan.require(moved.add(positions[i]), "Cycles in one step must be disjoint; split composition into steps");
                    }
                    for (int i = 0; i < positions.length; i++) {
                        int destination = positions[(i + 1) % positions.length];
                        current[destination] = before[positions[i]];
                    }
                    cycles.add(positions);
                }
                // Blank identity is stable even when its position participates in an abstract cycle.
                if (proof.has("blank")) {
                    for (int i = 0; i < current.length; i++) { if (current[i] == blankIdentity) { blank = i; } }
                }
                states.add(current.clone());
            }
            hasAlgebra |= algebra;
            steps.add(new Step(text, List.copyOf(rows), highlight, Set.copyOf(focus), List.copyOf(edges),
                    List.copyOf(states), algebra || mode.equals("permutation"), List.copyOf(cycles)));
        }
        return new ProofScene(mode, vertices, labels, root, blankIdentity, steps, hasRows, hasAlgebra, proof.path("pointer").asBoolean());
    }

    Frame frame(JsonNode timing, double seconds, double progress) {
        JsonNode times = timing.path("visualTimes");
        int index;
        double fraction;
        if (times.isArray() && !times.isEmpty()) {
            ProductionPlan.require(times.size() == steps.size(), "Proof visualTimes count must match steps");
            double previous = -1;
            for (JsonNode time : times) {
                double value = time.asDouble(Double.NaN);
                ProductionPlan.require(time.isNumber() && Double.isFinite(value) && value >= 0 && value >= previous,
                        "Proof visualTimes must be finite, nonnegative and ordered");
                previous = value;
            }
            index = 0;
            while (index + 1 < times.size() && seconds >= times.get(index + 1).asDouble()) { index++; }
            double start = times.get(index).asDouble();
            double end = index + 1 < times.size() ? times.get(index + 1).asDouble()
                    : timing.path("frames").asDouble() / timing.path("fps").asInt(30);
            fraction = seconds < start ? 0 : Math.min(1, (seconds - start) / Math.max(0.001, (end - start) * 0.75));
        } else {
            double position = Math.max(0, Math.min(1, progress)) * steps.size();
            index = Math.min(steps.size() - 1, (int) position);
            fraction = Math.min(1, (position - index) / 0.75);
        }
        Step step = steps.get(index);
        double position = fraction * (step.states().size() - 1);
        int state = Math.min(step.states().size() - 1, (int) position);
        int next = Math.min(step.states().size() - 1, state + 1);
        double sub = Math.min(1, (position - state) / 0.82);
        return new Frame(step, index, step.states().get(state), step.states().get(next), sub * sub * (3 - 2 * sub));
    }

    Map<String, String> finalTokens() {
        int[] state = steps.getLast().states().getLast();
        var result = new LinkedHashMap<String, String>();
        for (int i = 0; i < state.length; i++) { result.put(vertices.get(i).id(), tokenLabels[state[i]]); }
        return result;
    }

    private static double coordinate(JsonNode node, String field) {
        JsonNode value = node.path(field);
        ProductionPlan.require(value.isNumber() && Double.isFinite(value.asDouble()) && value.asDouble() >= 0 && value.asDouble() <= 1,
                "Proof coordinate outside [0,1]: " + field);
        return value.asDouble();
    }

    private static int nodeIndex(JsonNode item, Map<String, Integer> ids) {
        ProductionPlan.require(item != null && item.isTextual() && ids.containsKey(item.asText()), "Unknown proof node");
        return ids.get(item.asText());
    }

    private static void addEdges(JsonNode list, Map<String, Integer> ids, Set<Edge> edges) {
        if (list.isMissingNode()) { return; }
        ProductionPlan.require(list.isArray(), "Proof edges must be an array");
        for (JsonNode pair : list) {
            ProductionPlan.require(pair.isArray() && pair.size() == 2, "A proof edge needs two endpoints");
            int a = nodeIndex(pair.get(0), ids);
            int b = nodeIndex(pair.get(1), ids);
            ProductionPlan.require(a != b, "Proof graphs cannot have self loops");
            edges.add(new Edge(a, b));
        }
    }

    private static List<String> rows(JsonNode source, String mode) {
        if (source.isMissingNode()) { return List.of(); }
        boolean diagram = mode.equals("graph") || mode.equals("permutation");
        ProductionPlan.require(source.isArray() && source.size() <= (diagram ? 5 : 7), "Split overflowing proof table into steps");
        var result = new ArrayList<String>();
        for (JsonNode row : source) {
            ProductionPlan.require(row.isTextual() && !row.asText().isBlank(), "Proof rows must be nonblank strings");
            bounded(row.asText(), diagram ? 34 : 68, "Proof row");
            result.add(row.asText());
        }
        return List.copyOf(result);
    }

    private static void bounded(String text, int maximum, String field) {
        ProductionPlan.require(!text.contains("\n") && !text.contains("\r") && text.codePointCount(0, text.length()) <= maximum,
                field + " is too long; split the display into steps");
    }
}
