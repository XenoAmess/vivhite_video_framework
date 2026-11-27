const TAU = Math.PI * 2;
const SERIF = '"Noto Serif SC", SimSun, serif';
const GOLD = "#ffdf99";
const LILAC = "#cdbcff";
const SINE_X = "#643491";
const SINE_Y = "#91601d";
const CONTACT_THETA = Math.PI / 4;
const CONTACT_PHI = CONTACT_THETA + 0.11;
const SCALE = 2;
const WIDTH = 1408;
const HEIGHT = 512;

function surface(width, height, alpha = true) {
    const canvas = document.createElement("canvas");
    canvas.width = width;
    canvas.height = height;
    return canvas.getContext("2d", { alpha });
}

function smooth(from, to, value) {
    const t = Math.max(0, Math.min(1, (value - from) / (to - from)));
    return t * t * (3 - 2 * t);
}

function randomSequence(seed) {
    return () => {
        seed = (1664525 * seed + 1013904223) >>> 0;
        return seed / 2 ** 32;
    };
}

function label(ctx, text, x, y, size, color, font = "Consolas", spacing = 0, weight = 400) {
    ctx.fillStyle = color;
    ctx.font = `${weight} ${size}px ${font}`;
    ctx.letterSpacing = `${spacing}px`;
    ctx.fillText(text, x, y);
    ctx.letterSpacing = "0px";
}

function line(ctx, x1, y1, x2, y2, color, width = 1) {
    ctx.beginPath();
    ctx.moveTo(x1, y1);
    ctx.lineTo(x2, y2);
    ctx.strokeStyle = color;
    ctx.lineWidth = width;
    ctx.stroke();
}

function stroke(ctx, sample, start, end, steps, color, width) {
    ctx.beginPath();
    ctx.moveTo(...sample(start));
    for (let index = 1; index <= steps; index++) {
        ctx.lineTo(...sample(start + (end - start) * index / steps));
    }
    ctx.strokeStyle = color;
    ctx.lineWidth = width;
    ctx.stroke();
}

function ellipse(ctx, x, y, rx, ry, angle, fill, outline, width = 1) {
    ctx.beginPath();
    ctx.ellipse(x, y, rx, ry, angle, 0, TAU);
    if (fill) {
        ctx.fillStyle = fill;
        ctx.fill();
    }
    if (outline) {
        ctx.strokeStyle = outline;
        ctx.lineWidth = width;
        ctx.stroke();
    }
}

function grid(ctx, x, y, width, height, unit, color) {
    ctx.beginPath();
    for (let col = x; col <= x + width; col += unit) {
        ctx.moveTo(col, y);
        ctx.lineTo(col, y + height);
    }
    for (let row = y; row <= y + height; row += unit) {
        ctx.moveTo(x, row);
        ctx.lineTo(x + width, row);
    }
    ctx.strokeStyle = color;
    ctx.lineWidth = 0.55;
    ctx.stroke();
}

function printGrain() {
    const ctx = surface(WIDTH, HEIGHT);
    const pixels = ctx.createImageData(WIDTH, HEIGHT);
    const random = randomSequence(2816024);
    for (let y = 0, i = 0; y < HEIGHT; y++) {
        const fiber = (random() - 0.5) * 12;
        for (let x = 0; x < WIDTH; x++, i += 4) {
            const fleck = 128 + fiber + (random() - 0.5) * 104 + 8 * Math.sin(x / 47) * Math.cos(y / 22);
            pixels.data.set([fleck, fleck, fleck, 255], i);
        }
    }
    ctx.putImageData(pixels, 0, 0);
    return ctx.canvas;
}

function tornPath(ctx, corners) {
    const random = randomSequence(24851);
    ctx.beginPath();
    ctx.moveTo(...corners[0]);
    for (let edge = 0; edge < corners.length; edge++) {
        const [x, y] = corners[edge];
        const [nextX, nextY] = corners[(edge + 1) % corners.length];
        const steps = Math.ceil(Math.hypot(nextX - x, nextY - y) / 4.5);
        for (let step = 1; step <= steps; step++) {
            const n = step / steps;
            const tear = Math.sin(step * 0.18) * 1.2 + (random() - 0.5) * 4;
            ctx.lineTo(x + (nextX - x) * n + tear * (nextY - y) / steps / 4.5,
                y + (nextY - y) * n - tear * (nextX - x) / steps / 4.5);
        }
    }
    ctx.closePath();
}

function background(ctx, words, grain, plot) {
    const paper = ctx.createLinearGradient(0, 0, WIDTH, HEIGHT);
    paper.addColorStop(0, "#ded5d8");
    paper.addColorStop(0.43, "#f3e9dd");
    paper.addColorStop(1, "#dcd9e9");
    ctx.fillStyle = paper;
    ctx.fillRect(0, 0, WIDTH, HEIGHT);
    grid(ctx, 14, 11, WIDTH - 24, HEIGHT - 22, 14, "#3e2d4931");

    ctx.save();
    tornPath(ctx, [[116, 32], [1309, 13], [1370, 453], [1259, 494], [53, 479]]);
    ctx.shadowColor = "#23182e76";
    ctx.shadowBlur = 18;
    ctx.shadowOffsetY = 4;
    const ink = ctx.createLinearGradient(250, 489, 1186, 0);
    ink.addColorStop(0, "#211d36");
    ink.addColorStop(0.60, "#312346");
    ink.addColorStop(1, "#131426");
    ctx.fillStyle = ink;
    ctx.fill();
    ctx.shadowColor = "transparent";
    ctx.clip();
    grid(ctx, 48, 4, 1326, 504, 30, "#e1d1f421");
    ctx.globalCompositeOperation = "soft-light";
    ctx.globalAlpha = 0.40;
    ctx.drawImage(grain, 0, 0);
    ctx.restore();

    const halo = ctx.createRadialGradient(700, 125, 13, 732, 204, 261);
    halo.addColorStop(0, "#fff5e8");
    halo.addColorStop(0.48, "#e8d9ed");
    halo.addColorStop(0.79, "#ada1c5");
    halo.addColorStop(1, "#6f5d924a");
    ellipse(ctx, 724, 219, 246, 177, -0.34, halo, "#d9c7e498", 0.9);
    for (let ring = 1; ring <= 8; ring++) {
        ellipse(ctx, 724, 219, 38 + ring * 24.2, 26 + ring * 18.1, -0.34, null, "#604c8261", 0.65);
    }
    ellipse(ctx, 720, 219, 265, 195, -0.34, null, "#dbc5f255", 0.65);
    for (let tick = 0; tick < 92; tick++) {
        const a = tick * TAU / 92;
        const x = 248 * Math.cos(a);
        const y = 178 * Math.sin(a);
        const px = 724 + 0.943 * x + 0.333 * y;
        const py = 219 - 0.333 * x + 0.943 * y;
        const inset = tick % 4 === 0 ? 0.95 : 0.984;
        line(ctx, px, py, 724 + (px - 724) * inset, 219 + (py - 219) * inset, "#49376086", 0.53);
    }

    // The right sheet tucks under the reaching arm. The equations are printed below its axes.
    const { cx, cy, rx, ry } = plot;
    ctx.save();
    const panel = ctx.createLinearGradient(1005, 385, 1340, 57);
    panel.addColorStop(0, "#372a4a");
    panel.addColorStop(1, "#18162e");
    tornPath(ctx, [[1012, 47], [1323, 58], [1303, 435], [1005, 417]]);
    ctx.shadowColor = "#130a228f";
    ctx.shadowBlur = 11;
    ctx.shadowOffsetY = 5;
    ctx.fillStyle = panel;
    ctx.fill();
    ctx.shadowColor = "transparent";
    ctx.strokeStyle = "#dcc9ee42";
    ctx.lineWidth = 0.75;
    ctx.stroke();
    ctx.clip();
    grid(ctx, cx - rx - 14, cy - ry - 10, (rx + 14) * 2, (ry + 11) * 2, 12.5, "#c0a9ea29");
    ctx.restore();

    line(ctx, cx - rx - 13, cy, cx + rx + 14, cy, "#dec8f485", 0.8);
    line(ctx, cx, cy + ry + 12, cx, cy - ry - 11, "#dec8f485", 0.8);
    label(ctx, words.axis[0], cx + rx + 4, cy - 5, 11, "#ddd0f0");
    label(ctx, words.axis[1], cx + 5, cy - ry + 8, 11, "#ddd0f0");
    line(ctx, 1020, 368, 1301, 368, "#cab7ec6e", 0.65);
    label(ctx, words.phasePlot, 1021, 388, 12, "#eee1f5", SERIF, 0.9, 700);
    label(ctx, words.phaseLabel, 1236, 388, 11, "#d4c3e9", SERIF);
    label(ctx, words.equations[0], 1022, 410, 13, LILAC);
    label(ctx, words.equations[1], 1178, 410, 13, GOLD);

    ctx.fillStyle = GOLD;
    ctx.fillRect(139, 85, 21, 2);
    label(ctx, words.character, 170, 90, 12, "#f0dfef", SERIF, 1.4);
    label(ctx, words.title, 125, 216, 103, "#f5edeb", SERIF, 10, 800);
    line(ctx, 137, 236, 380, 236, "#d4bbe7a0", 0.8);
    label(ctx, words.titleEnglish, 137, 266, 24, "#e0cfec", "Georgia", 5);
    for (const [x, y] of [[44, 58], [40, 443], [1364, 61], [1358, 478]]) {
        line(ctx, x - 6, y, x + 6, y, "#66517b82", 0.6);
        line(ctx, x, y - 6, x, y + 6, "#66517b82", 0.6);
    }
}

function waveCard(ctx, words, theta, phi) {
    ctx.save();
    ctx.translate(112, 329);
    ctx.rotate(-0.041);
    ctx.shadowColor = "#1a1129ac";
    ctx.shadowBlur = 11;
    ctx.shadowOffsetY = 5;
    ctx.fillStyle = "#f0e6e8";
    ctx.fillRect(0, 0, 335, 120);
    ctx.shadowColor = "transparent";
    label(ctx, words.wavePlot, 15, 20, 12, "#352644", SERIF, 0.85, 700);
    const [left, center, width] = [15, 66, 303];
    grid(ctx, left, 34, width, 62, 12, "#5a427239");
    line(ctx, left, center, left + width, center, "#64458070", 0.6);
    for (const [symbol, freq, offset, color, legendX] of [
        [words.axis[0], 3, phi, SINE_X, 258], [words.axis[1], 2, 0, SINE_Y, 294],
    ]) {
        line(ctx, legendX - 12, 16, legendX - 3, 16, color, 1.6);
        label(ctx, symbol, legendX, 20, 12, color);
        const sample = (u) => [left + width * u / TAU, center - 24 * Math.sin(freq * u + offset)];
        stroke(ctx, sample, 0, TAU, 180, color, 1.4);
        const [x, y] = sample(theta);
        ctx.globalAlpha = smooth(0, 0.24, theta) * smooth(0, 0.24, TAU - theta);
        line(ctx, x, 34, x, 96, "#5037617b", 0.68);
        ellipse(ctx, x, y, 2.8, 2.8, 0, color, "#fffbec", 0.75);
        ctx.globalAlpha = 1;
    }
    for (const [value, x] of [[words.axis[3], left], [words.axis[4], 163], [words.axis[5], 309]]) {
        label(ctx, value, x, 110, 11, "#554362");
    }
    label(ctx, words.axis[2], 319, 94, 10, "#554362");
    ctx.restore();
}

function diagram(ctx, plot, theta, phi) {
    const { cx, cy, rx, ry } = plot;
    const sample = (u, shift = 0) => [cx + rx * Math.sin(3 * u + phi + shift), cy - ry * Math.sin(2 * u)];
    for (const [shift, color, width] of [[-0.15, "#ae8de95b", 0.65], [0.15, "#d6b99875", 0.65], [0, "#d7c6f6", 1.18]]) {
        stroke(ctx, (u) => sample(u, shift), 0, TAU, 252, color, width);
    }
    ctx.save();
    ctx.shadowColor = "#dac2ff";
    ctx.shadowBlur = 7;
    stroke(ctx, sample, theta - 0.30, theta, 36, "#ffe3aa", 1.65);
    ctx.restore();
    return sample(theta);
}

function light(ctx, x, y, radius, focus) {
    const glow = ctx.createRadialGradient(x, y, 0, x, y, radius * 2.95);
    glow.addColorStop(0, "#fff8df");
    glow.addColorStop(0.13, "#ffe0a4d8");
    glow.addColorStop(0.38, "#ad8ee478");
    glow.addColorStop(1, "#9c7ace00");
    ellipse(ctx, x, y, radius * 2.95, radius * 2.95, 0, glow);
    ctx.fillStyle = "#fff8e8";
    ctx.beginPath();
    ctx.moveTo(x - radius * 1.47, y);
    ctx.quadraticCurveTo(x - 1.2, y - 1.8, x, y - radius * 0.8);
    ctx.quadraticCurveTo(x + 1.2, y - 1.8, x + radius * 1.47, y);
    ctx.quadraticCurveTo(x + 1.2, y + 1.8, x, y + radius * 0.8);
    ctx.quadraticCurveTo(x - 1.2, y + 1.8, x - radius * 1.47, y);
    ctx.fill();
    ctx.save();
    ctx.globalAlpha = focus;
    ellipse(ctx, x, y, 25 + 8 * focus, 7, -0.31, null, "#ffd893b8", 0.65);
    ellipse(ctx, x, y, 27 + 11 * focus, 10, 0.37, null, "#e6d0f1a2", 0.65);
    ctx.restore();
}

function stream(ctx, fingertip, phase, front, focus) {
    const [x, y] = fingertip;
    const sway = 7 * Math.sin(phase);
    const gradient = ctx.createLinearGradient(394, 445, x, y);
    gradient.addColorStop(0, "#d8b6fe00");
    gradient.addColorStop(0.37, front ? "#b0a0efd0" : "#a48ac477");
    gradient.addColorStop(0.72, front ? "#f8dba7b8" : "#e9c9fd90");
    gradient.addColorStop(1, front ? "#fff0bbc8" : "#e7caffb8");
    ctx.save();
    ctx.globalAlpha = 0.62 + 0.26 * focus;
    for (const spread of [-2, -1, 0, 1.2, 2.4]) {
        ctx.beginPath();
        if (front) {
            ctx.moveTo(367, 444 + spread * 7);
            ctx.bezierCurveTo(649, 576 + spread * 10 + sway, 994, 367 - spread * 14, x + 13, y + 3);
        } else {
            ctx.moveTo(389, 385 + spread * 9);
            ctx.bezierCurveTo(654, 139 + spread * 17 - sway, 877, 247 + spread * 13, x + 9, y - 4);
        }
        ctx.strokeStyle = gradient;
        ctx.lineWidth = spread === 0 ? 1.58 : 0.58;
        ctx.stroke();
    }
    ctx.restore();
}

function swing(x, y, [pivotX, pivotY], angle) {
    const dx = x - pivotX;
    const dy = y - pivotY;
    return [pivotX + dx * Math.cos(angle) - dy * Math.sin(angle),
        pivotY + dx * Math.sin(angle) + dy * Math.cos(angle)];
}

function posePoint(rawX, rawY, phase, landmarks) {
    const reach = 0.5 - 0.5 * Math.cos(phase);
    const arm = smooth(875, 1130, rawX) * (1 - smooth(330, 471, rawY));
    const hand = smooth(1272, 1400, rawX) * (1 - smooth(248, 318, rawY));
    const hair = (1 - smooth(247, 364, rawY)) * smooth(460, 555, rawX) * (1 - smooth(886, 940, rawX));
    const sash = (1 - smooth(260, 479, rawX)) * smooth(333, 440, rawY) * (1 - smooth(573, 691, rawY));
    const backArm = (1 - smooth(207, 469, rawX)) * smooth(662, 861, rawY);
    const hem = smooth(636, 907, rawY) * smooth(404, 578, rawX) * (1 - smooth(919, 1093, rawX));
    let [x, y] = swing(rawX, rawY, landmarks.wrist, hand * (0.035 - 0.091 * reach));
    [x, y] = swing(x, y, landmarks.shoulder, arm * (0.043 - 0.076 * reach));
    [x, y] = swing(x, y, landmarks.neck, hair * 0.037 * Math.sin(phase + 0.55));
    x += 17 * arm * reach - 13 * backArm * reach + 6 * hem * Math.sin(phase - 0.35);
    y += 16 * sash * Math.sin(phase - 0.48 + 0.005 * rawX)
        + backArm * 8 * reach + 4 * hem * Math.cos(phase - 0.35);
    return [361 + 0.532 * x + 3.1 * Math.sin(phase), 25 + 0.532 * y + 2.2 * Math.cos(phase - 0.35)];
}

function buildMesh(portrait) {
    const cols = 37;
    const rows = 25;
    const vertices = new Float32Array(rows * cols * 2);
    const uvs = new Float32Array(vertices.length);
    const indices = [];
    for (let row = 0; row < rows; row++) {
        for (let col = 0; col < cols; col++) {
            const start = row * cols + col;
            uvs[2 * start] = col / (cols - 1);
            uvs[2 * start + 1] = row / (rows - 1);
            if (col + 1 < cols && row + 1 < rows) {
                indices.push(start, start + 1, start + cols, start + cols,
                    start + 1, start + cols + 1);
            }
        }
    }
    const texture = PIXI.Texture.from(portrait);
    const mesh = new PIXI.SimpleMesh(texture, vertices, uvs, new Uint16Array(indices), PIXI.DRAW_MODES.TRIANGLES);
    return { mesh, vertices, uvs };
}

async function prepare() {
    const plan = await (await fetch("/production-plan.json")).json();
    const portrait = new Image();
    portrait.src = "/portrait.png";
    await Promise.all([portrait.decode(), document.fonts.load(`800 103px ${SERIF}`, plan.screenText.title)]);
    const base = surface(plan.width, plan.height);
    const output = surface(plan.width, plan.height, false);
    const actor = surface(plan.width, plan.height);
    const grain = printGrain();
    const renderer = new PIXI.Renderer({
        width: plan.width, height: plan.height, backgroundAlpha: 0, antialias: true, preserveDrawingBuffer: true,
    });
    const { mesh, vertices, uvs } = buildMesh(portrait);
    const project = (x, y, phase) => posePoint(x, y, phase, plan.landmarks);
    const [touchX, touchY] = project(...plan.landmarks.fingertip, Math.PI);
    const rx = 121;
    const plot = { cx: touchX + 16 - rx * Math.sin(3 * CONTACT_THETA + CONTACT_PHI),
        cy: touchY + 145, rx, ry: 137 };
    const random = randomSequence(622193);
    const motes = Array.from({ length: 76 }, () => ({
        x: 434 + random() * 790, y: 63 + random() * 389,
        size: 0.45 + random() * 0.95, phase: TAU * random(),
    }));
    base.scale(SCALE, SCALE);
    background(base, plan.screenText, grain, plot);
    window.renderInfo = { portraitSize: [portrait.naturalWidth, portrait.naturalHeight], meshVertices: vertices.length / 2, plot };

    window.renderFrame = (frame, capture) => {
        if (!capture) {
            return null;
        }
        const phase = frame / plan.frameCount * TAU;
        // Slow the common sample parameter at the fingertip, while taking one turn per loop.
        const theta = (phase + Math.sin(phase) + TAU - Math.PI + CONTACT_THETA) % TAU;
        const phi = CONTACT_PHI + 0.32 * (1 + Math.cos(phase));
        const fingertip = project(...plan.landmarks.fingertip, phase);
        const focus = (0.5 - 0.5 * Math.cos(phase)) ** 9;
        for (let i = 0; i < vertices.length; i += 2) {
            const [x, y] = project(uvs[i] * portrait.naturalWidth, uvs[i + 1] * portrait.naturalHeight, phase);
            vertices[i] = x * SCALE;
            vertices[i + 1] = y * SCALE;
        }
        renderer.render(mesh);

        actor.setTransform(1, 0, 0, 1, 0, 0);
        actor.clearRect(0, 0, plan.width, plan.height);
        actor.drawImage(renderer.view, 0, 0);
        actor.setTransform(SCALE, 0, 0, SCALE, 0, 0);
        actor.save();
        actor.globalCompositeOperation = "source-atop";
        const [hx, hy] = fingertip;
        const tint = actor.createRadialGradient(hx, hy, 1, hx, hy, 135);
        tint.addColorStop(0, `rgba(255,217,139,${0.30 * focus})`);
        tint.addColorStop(1, "rgba(247,208,133,0)");
        actor.fillStyle = tint;
        actor.fillRect(hx - 135, hy - 135, 270, 270);
        actor.restore();

        output.setTransform(1, 0, 0, 1, 0, 0);
        output.drawImage(base.canvas, 0, 0);
        output.setTransform(SCALE, 0, 0, SCALE, 0, 0);
        stream(output, fingertip, phase, false, focus);
        const point = diagram(output, plot, theta, phi);
        for (const mote of motes) {
            output.globalAlpha = 0.18 + 0.39 * (0.5 + 0.5 * Math.sin(phase + mote.phase)) ** 2;
            const x = mote.x + 6 * Math.sin(phase + mote.phase);
            const y = mote.y + 7 * Math.cos(phase + mote.phase);
            ellipse(output, x, y, mote.size, mote.size, 0, mote.phase < Math.PI ? GOLD : LILAC);
        }
        output.globalAlpha = 1;
        output.drawImage(actor.canvas, 0, 0, WIDTH, HEIGHT);
        waveCard(output, plan.screenText, theta, phi);
        stream(output, fingertip, phase, true, focus);
        light(output, ...point, 6.4 + 7 * focus, focus);
        output.save();
        output.globalCompositeOperation = "soft-light";
        output.globalAlpha = 0.19;
        output.drawImage(grain, 0, 0);
        output.restore();
        return output.canvas.toDataURL("image/png").split(",", 2)[1];
    };
}

prepare().catch((error) => { window.renderError = error.stack; });
