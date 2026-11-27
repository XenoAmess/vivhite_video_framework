const TAU = 2 * Math.PI;
const INK = "#211e32";
const GOLD = "#f7cd78";
const LILAC = "#c0adff";
const PAPER = "#f0ecf2";
const SERIF = '"Noto Serif SC", SimSun, serif';
const MONO = 'Consolas, monospace';

function surface(width, height, alpha = true) {
    const canvas = document.createElement("canvas");
    canvas.width = width;
    canvas.height = height;
    return canvas.getContext("2d", { alpha });
}

function randomSequence(seed) {
    return () => {
        seed = (1664525 * seed + 1013904223) >>> 0;
        return seed / 2 ** 32;
    };
}

function line(ctx, x1, y1, x2, y2, color, width = 1) {
    ctx.beginPath();
    ctx.moveTo(x1, y1);
    ctx.lineTo(x2, y2);
    ctx.lineWidth = width;
    ctx.strokeStyle = color;
    ctx.stroke();
}

function path(ctx, sample, from, to, steps) {
    ctx.beginPath();
    const [x, y] = sample(from);
    ctx.moveTo(x, y);
    for (let index = 1; index <= steps; index++) {
        ctx.lineTo(...sample(from + (to - from) * index / steps));
    }
}

function ellipse(ctx, x, y, rx, ry, angle, fill, stroke, width = 1) {
    ctx.beginPath();
    ctx.ellipse(x, y, rx, ry, angle, 0, TAU);
    if (fill) {
        ctx.fillStyle = fill;
        ctx.fill();
    }
    if (stroke) {
        ctx.strokeStyle = stroke;
        ctx.lineWidth = width;
        ctx.stroke();
    }
}

function label(ctx, value, x, y, size, color, { font = MONO, weight = 400, spacing = 0 } = {}) {
    ctx.fillStyle = color;
    ctx.font = `${weight} ${size}px ${font}`;
    ctx.letterSpacing = `${spacing}px`;
    ctx.fillText(value, x, y);
    ctx.letterSpacing = "0px";
}

function cross(ctx, x, y, size, color) {
    line(ctx, x - size, y, x + size, y, color, 0.6);
    line(ctx, x, y - size, x, y + size, color, 0.6);
}

function grid(ctx, x, y, width, height, spacing, color) {
    ctx.beginPath();
    for (let column = x; column <= x + width; column += spacing) {
        ctx.moveTo(column, y);
        ctx.lineTo(column, y + height);
    }
    for (let row = y; row <= y + height; row += spacing) {
        ctx.moveTo(x, row);
        ctx.lineTo(x + width, row);
    }
    ctx.strokeStyle = color;
    ctx.lineWidth = 0.55;
    ctx.stroke();
}

function grain(width, height) {
    const ctx = surface(width, height);
    const pixels = ctx.createImageData(width, height);
    const random = randomSequence(351967);
    for (let y = 0, index = 0; y < height; y++) {
        const fiber = (random() - 0.5) * 11;
        for (let x = 0; x < width; x++, index += 4) {
            const cloud = 10 * Math.sin((x + y * 1.37) / 18) * Math.cos(y / 23);
            const tone = 126 + fiber + cloud + (random() - 0.5) * 115;
            pixels.data[index] = tone;
            pixels.data[index + 1] = tone;
            pixels.data[index + 2] = tone;
            pixels.data[index + 3] = 255;
        }
    }
    ctx.putImageData(pixels, 0, 0);
    return ctx.canvas;
}

function tornSheet(ctx) {
    const random = randomSequence(54980);
    const corners = [[143, 14], [1346, 36], [1300, 483], [68, 510]];
    ctx.beginPath();
    ctx.moveTo(...corners[0]);
    for (let side = 0; side < corners.length; side++) {
        const [ax, ay] = corners[side];
        const [bx, by] = corners[(side + 1) % corners.length];
        const steps = Math.ceil(Math.hypot(bx - ax, by - ay) / 4);
        for (let step = 1; step <= steps; step++) {
            const k = step / steps;
            const tear = Math.sin(step * 0.19) * 1.6 + (random() - 0.5) * 5;
            ctx.lineTo(ax + (bx - ax) * k + tear * (by - ay) / steps / 4,
                ay + (by - ay) * k - tear * (bx - ax) / steps / 4);
        }
    }
    ctx.closePath();
}

function drawPaper(ctx, width, height, texture) {
    const linen = ctx.createLinearGradient(0, 0, width, height);
    linen.addColorStop(0, "#e5ded6");
    linen.addColorStop(0.60, "#faf1e7");
    linen.addColorStop(1, "#d9d5e2");
    ctx.fillStyle = linen;
    ctx.fillRect(0, 0, width, height);
    grid(ctx, 12, 11, width - 23, height - 22, 14, "#29203917");
    ctx.save();
    tornSheet(ctx);
    ctx.shadowColor = "#2c214967";
    ctx.shadowBlur = 12;
    ctx.shadowOffsetY = 4;
    const ink = ctx.createLinearGradient(88, 464, 1280, 32);
    ink.addColorStop(0, "#242035");
    ink.addColorStop(0.52, "#30253f");
    ink.addColorStop(1, "#1b1c31");
    ctx.fillStyle = ink;
    ctx.fill();
    ctx.shadowColor = "transparent";
    ctx.clip();
    grid(ctx, 90, 8, 1260, 496, 28, "#d3c2f328");
    grid(ctx, 90, 8, 1260, 496, 7, "#c8b5ef08");
    ctx.globalCompositeOperation = "soft-light";
    ctx.globalAlpha = 0.45;
    ctx.drawImage(texture, 0, 0, width, height);
    ctx.restore();
    for (const [x, y] of [[45, 66], [38, 448], [1364, 59], [1354, 444]]) {
        cross(ctx, x, y, 7, "#4e385c");
        ellipse(ctx, x, y, 2.6, 2.6, 0, null, "#4e385c", 0.6);
    }
    ctx.save();
    ctx.translate(1363, 150);
    ctx.rotate(Math.PI / 2);
    for (let index = 0; index <= 38; index++) {
        const y = index % 5 === 0 ? 14 : 6;
        line(ctx, index * 6.0, 0, index * 6.0, y, "#3326409c", 0.65);
    }
    ctx.restore();
}

function drawHalo(ctx) {
    const x = 737;
    const y = 219;
    const halo = ctx.createRadialGradient(688, 124, 15, x, y, 205);
    halo.addColorStop(0, "#fff3de");
    halo.addColorStop(0.66, "#dfd5ea");
    halo.addColorStop(1, "#b9a9d2");
    ctx.save();
    ctx.shadowColor = "#171326ac";
    ctx.shadowBlur = 21;
    ctx.shadowOffsetY = 9;
    ellipse(ctx, x, y, 201, 193, -0.13, halo);
    ctx.restore();
    for (let radius = 32; radius <= 195; radius += 16) {
        ellipse(ctx, x + 3, y, radius, radius * 0.96, -0.13, null, "#5541663d", 0.6);
    }
    ellipse(ctx, x - 3, y + 1, 216, 204, -0.13, null, "#c5aae06f", 0.8);
    for (let tick = 0; tick < 72; tick++) {
        const a = tick * TAU / 72;
        const length = tick % 6 === 0 ? 11 : 4;
        line(ctx, x + 189 * Math.cos(a), y + 181 * Math.sin(a),
            x + (189 - length) * Math.cos(a), y + (181 - length) * Math.sin(a), "#5541668f", 0.58);
    }
    for (const [px, py] of [[559, 141], [855, 85], [912, 164], [899, 302]]) {
        cross(ctx, px, py, 5, "#534163a0");
    }
}

function drawTitles(ctx, words) {
    ctx.fillStyle = GOLD;
    ctx.fillRect(147, 84, 24, 3);
    label(ctx, words.character, 182, 89, 12, "#eee2f7", { spacing: 2.2 });
    label(ctx, words.title, 139, 223, 105, "#f4edf4", { font: SERIF, weight: 800, spacing: 12 });
    line(ctx, 148, 244, 407, 244, "#b6a7d8", 0.7);
    ellipse(ctx, 408, 244, 2, 2, 0, GOLD);
    label(ctx, words.titleEnglish, 149, 277, 27, "#d9c9e8",
        { font: 'Georgia, serif', spacing: 5.5 });
}

function card(ctx, x, y, width, height, angle, fill) {
    ctx.translate(x, y);
    ctx.rotate(angle);
    ctx.shadowColor = "#100a29a0";
    ctx.shadowBlur = 11;
    ctx.shadowOffsetY = 6;
    ctx.fillStyle = fill;
    ctx.fillRect(0, 0, width, height);
    ctx.shadowColor = "transparent";
    ctx.strokeStyle = "#aa94c9a0";
    ctx.lineWidth = 0.8;
    ctx.strokeRect(0.5, 0.5, width - 1, height - 1);
}

function flare(ctx, x, y, size, alpha = 1) {
    ctx.save();
    ctx.globalAlpha = alpha;
    const glow = ctx.createRadialGradient(x, y, 0, x, y, size * 1.95);
    glow.addColorStop(0, "#fff7e9");
    glow.addColorStop(0.11, "#ffe0a9d9");
    glow.addColorStop(0.35, "#d9aeff80");
    glow.addColorStop(1, "#9e7cec00");
    ellipse(ctx, x, y, size * 1.95, size * 1.95, 0, glow);
    ctx.fillStyle = "#fffaec";
    ctx.beginPath();
    ctx.moveTo(x - size * 1.5, y);
    ctx.quadraticCurveTo(x - 2, y - 1, x, y - size * 0.65);
    ctx.quadraticCurveTo(x + 2, y - 1, x + size * 1.5, y);
    ctx.quadraticCurveTo(x + 2, y + 1, x, y + size * 0.65);
    ctx.quadraticCurveTo(x - 2, y + 1, x - size * 1.5, y);
    ctx.fill();
    ctx.restore();
}

function phaseCard(ctx, words, theta, phi) {
    ctx.save();
    card(ctx, 1037, 112, 258, 251, 0.035, "#211c34");
    grid(ctx, 16, 40, 226, 166, 11, "#bba7f227");
    label(ctx, words.phasePlot, 16, 25, 14, PAPER, { font: SERIF, spacing: 1.4 });
    line(ctx, 16, 33, 242, 33, "#d0beed81", 0.65);
    line(ctx, 16, 123, 242, 123, "#d0beed70", 0.65);
    line(ctx, 129, 40, 129, 206, "#d0beed70", 0.65);
    label(ctx, words.axis[0], 233, 118, 10, "#d7c9ed");
    label(ctx, words.axis[1], 134, 50, 10, "#d7c9ed");
    const plot = (u, shift = 0) => [129 + 96 * Math.sin(3 * u + phi + shift), 123 - 69 * Math.sin(2 * u)];
    for (const [shift, color] of [[-0.12, "#c083c82e"], [0.12, "#b5a3fb55"], [0, "#d5c5ff"]]) {
        path(ctx, (u) => plot(u, shift), 0, TAU, 210);
        ctx.strokeStyle = color;
        ctx.lineWidth = shift ? 0.8 : 1.2;
        ctx.stroke();
    }
    path(ctx, (u) => plot(u), theta - 0.24, theta, 36);
    ctx.strokeStyle = GOLD;
    ctx.lineWidth = 1.6;
    ctx.stroke();
    const [x, y] = plot(theta);
    flare(ctx, x, y, 6.4);
    label(ctx, words.equations, 16, 231, 12, "#e3d1f1");
    ctx.restore();
    return [1037 + x * Math.cos(0.035) - y * Math.sin(0.035),
        112 + x * Math.sin(0.035) + y * Math.cos(0.035)];
}

function waveCard(ctx, words, theta, phi) {
    ctx.save();
    card(ctx, 118, 347, 399, 113, -0.028, "#efe6e7");
    grid(ctx, 17, 34, 365, 57, 12, "#4b346438");
    label(ctx, words.wavePlot, 17, 23, 12, INK, { font: SERIF, spacing: 1.2 });
    line(ctx, 17, 63, 382, 63, "#65527d66", 0.55);
    for (const [frequency, shift, color] of [[3, phi, "#71429f"], [2, 0, "#996124"]]) {
        const sample = (u) => [18 + 362 * u / TAU, 63 - 20 * Math.sin(frequency * u + shift)];
        path(ctx, sample, 0, TAU, 180);
        ctx.strokeStyle = color;
        ctx.lineWidth = 1.35;
        ctx.stroke();
        const [x, y] = sample(theta);
        line(ctx, x, 36, x, 91, "#51345e7a", 0.5);
        ellipse(ctx, x, y, 2.7, 2.7, 0, color, "#fff5e9", 0.8);
    }
    for (const [index, x] of [[3, 17], [4, 195], [5, 370]]) {
        label(ctx, words.axis[index], x, 104, 9, "#534160");
    }
    label(ctx, words.axis[2], 370, 23, 11, "#413051");
    ctx.restore();
}

function orbitPoint(u, band = 0) {
    const x = (434 + band * 7) * Math.cos(u);
    const y = (115 + band * 8) * Math.sin(u) + 9 * Math.sin(2 * u + band * 0.3);
    return [759 + 0.970 * x + 0.243 * y, 292 - 0.243 * x + 0.970 * y];
}

function orbits(ctx, phase, front) {
    const [from, to] = front ? [0.08, Math.PI - 0.12] : [Math.PI - 0.12, TAU + 0.08];
    ctx.save();
    const shine = ctx.createLinearGradient(347, 405, 1192, 183);
    shine.addColorStop(0, "#b1a1fa12");
    shine.addColorStop(0.30, "#e1c3ffb5");
    shine.addColorStop(0.64, "#fff3c4e0");
    shine.addColorStop(1, "#9c9cf55d");
    for (const [band, color, width] of [[-1.6, "#997ed585", 0.7], [-0.7, "#cfb4e580", 0.8],
        [0, shine, front ? 1.65 : 1.15], [0.9, "#e7c782b0", 0.75], [1.8, "#e8c8ec64", 0.55]]) {
        path(ctx, (u) => orbitPoint(u, band), from, to, 130);
        ctx.strokeStyle = color;
        ctx.lineWidth = width;
        ctx.stroke();
    }
    if (front) {
        const comet = 1.20 + 0.76 * Math.cos(phase + 0.7);
        path(ctx, orbitPoint, comet - 0.17, comet, 28);
        ctx.strokeStyle = "#fff0cf";
        ctx.lineWidth = 1.9;
        ctx.shadowBlur = 9;
        ctx.shadowColor = "#e7c6f3";
        ctx.stroke();
        ctx.shadowColor = "transparent";
        flare(ctx, ...orbitPoint(comet), 9 + 3 * Math.sin(phase) ** 2);
    }
    ctx.restore();
}

function palmLight(ctx, phase, [targetX, targetY]) {
    const peak = Math.max(0, Math.cos(phase - 3.0));
    const intensity = peak ** 5;
    if (intensity < 0.002) {
        return;
    }
    const x = 815 + 4 * Math.sin(phase);
    const y = 216 + 37 * (1 - peak) + 6 * Math.sin(phase);
    ctx.save();
    ctx.globalAlpha = 0.69 * intensity;
    const filament = ctx.createLinearGradient(x, y, targetX, targetY);
    filament.addColorStop(0, "#fff0b9");
    filament.addColorStop(0.72, "#e0c9f7a3");
    filament.addColorStop(1, "#c2aefa2f");
    ctx.beginPath();
    ctx.moveTo(x, y);
    ctx.bezierCurveTo(x + 101, y - 61, targetX - 50, targetY + 30, targetX, targetY);
    ctx.strokeStyle = filament;
    ctx.lineWidth = 0.95;
    ctx.stroke();
    for (const [rx, ry, angle] of [[30, 8, -0.23], [26, 9, 0.41], [23, 10, -0.64]]) {
        ellipse(ctx, x, y, rx, ry, angle + 0.23 * Math.sin(phase), null, "#f9d586bd", 0.6);
    }
    ctx.restore();
    flare(ctx, x, y, 10, intensity);
}

function drawDust(ctx, phase, motes) {
    for (const { x, y, radius, offset } of motes) {
        const opacity = 0.14 + 0.43 * (0.5 + 0.5 * Math.sin(phase + offset)) ** 3;
        ctx.globalAlpha = opacity;
        const px = x + 3.9 * Math.cos(phase + offset);
        const py = y + 4.0 * Math.sin(phase + offset);
        ellipse(ctx, px, py, radius, radius, 0, offset > Math.PI ? GOLD : LILAC);
    }
    ctx.globalAlpha = 1;
}

function blink(frame, center) {
    const offset = frame - center;
    const half = offset < 0 ? 3 : 5;
    return Math.abs(offset) < half ? (1 + Math.cos(Math.PI * offset / half)) * 0.5 : 0;
}

function movement(frame, phase) {
    const turn = (1 - Math.cos(phase)) * 0.5;
    const smile = Math.sin(phase * 0.5) ** 6;
    const close = Math.max(blink(frame, 61), blink(frame, 127));
    return {
        ParamAngleX: 2 + 7 * Math.sin(phase - 0.28),
        ParamAngleY: -1 + 4 * Math.sin(phase - 0.90),
        ParamAngleZ: -4 + 4.3 * Math.sin(phase + 0.28),
        ParamBodyAngleX: 2.6 * Math.sin(phase - 0.5),
        ParamBodyAngleZ: -1.2 + 1.9 * Math.sin(phase - 0.25),
        ParamEyeBallX: 0.035 + 0.46 * Math.sin(phase + 0.28),
        ParamEyeBallY: -0.08 - 0.16 * Math.sin(phase),
        ParamEyeLOpen: 1 - 0.97 * close,
        ParamEyeROpen: 1 - 0.97 * close,
        ParamMouthForm: 0.17 + 0.48 * smile,
        ParamMouthOpenY: 0,
        ParamBreath: 0.44 + 0.33 * Math.sin(phase - 0.4),
        LAU: -6 - 13 * turn,
        LAD: -9 - 18 * turn,
        LHand: 3 + 9 * turn,
        RAU: -7 + 5 * turn,
        RAD: -5 - 5 * turn,
    };
}

async function prepare() {
    const plan = await (await fetch("/production-plan.json")).json();
    const { width, height, fps, frameCount, screenText } = plan;
    const output = surface(width, height, false);
    const logicalWidth = width / 2;
    const logicalHeight = height / 2;
    const base = surface(width, height);
    const texture = grain(logicalWidth, logicalHeight);
    await Promise.all([document.fonts.load(`800 105px ${SERIF}`, screenText.title), document.fonts.ready]);
    base.scale(2, 2);
    drawPaper(base, logicalWidth, logicalHeight, texture);
    drawHalo(base);
    drawTitles(base, screenText);
    const random = randomSequence(63955);
    const motes = Array.from({ length: 64 }, () => ({
        x: 428 + random() * 740, y: 75 + random() * 373, radius: 0.45 + random() * 0.96,
        offset: random() * TAU,
    }));

    const renderer = new PIXI.Renderer({
        width, height, antialias: true, backgroundAlpha: 0, preserveDrawingBuffer: true,
    });
    const model = await PIXI.live2d.Live2DModel.from(`/model/${plan.model}`, {
        autoUpdate: false, autoInteract: false,
    });
    const internal = model.internalModel;
    const nativeParameters = internal.coreModel._model.parameters;
    const bindings = Object.entries(movement(0, 0)).map(([name]) => {
        const index = nativeParameters.ids.indexOf(name);
        if (index < 0) {
            throw new Error(`Required Live2D parameter missing: ${name}`);
        }
        return [name, index];
    });
    if (!internal.physics) {
        throw new Error("The Delta physics rig failed to load.");
    }
    internal.eyeBlink = undefined;
    internal.breath = undefined;
    let pose;
    internal.on("afterMotionUpdate", () => {
        for (const [name, index] of bindings) {
            internal.coreModel.setParameterValueByIndex(index, pose[name]);
        }
    });
    model.anchor.set(0.5, 0.18);
    model.scale.set(height / model.height * 2.42);

    function tick(frame) {
        const phase = frame / frameCount * TAU;
        pose = movement(frame, phase);
        model.position.set((736 + 2.7 * Math.sin(phase)) * 2, (103 + 2.2 * Math.sin(phase - 0.4)) * 2);
        model.rotation = -0.064 + 0.014 * Math.sin(phase - 0.3);
        model.update(1000 / fps);
        renderer.render(model);
        return phase;
    }

    window.renderInfo = {
        modelCanvas: [internal.originalWidth, internal.originalHeight],
        cubismCoreVersion: Live2DCubismCore.Version.csmGetVersion(),
        maxTextureSize: renderer.gl.getParameter(renderer.gl.MAX_TEXTURE_SIZE),
        drivenParameters: bindings.map(([name]) => name),
    };
    // Prime the physics with the same periodic movement used by the output.
    for (let frame = 0; frame < frameCount; frame++) {
        tick(frame);
    }
    window.renderFrame = (frame, capture) => {
        const phase = tick(frame);
        if (!capture) {
            return null;
        }
        const phi = 0.56 + 0.57 * (1 - Math.cos(phase));
        const theta = Math.PI * (1 - Math.cos(phase + 0.27));
        output.setTransform(1, 0, 0, 1, 0, 0);
        output.drawImage(base.canvas, 0, 0);
        output.setTransform(2, 0, 0, 2, 0, 0);
        orbits(output, phase, false);
        drawDust(output, phase, motes);
        const plottedPoint = phaseCard(output, screenText, theta, phi);
        waveCard(output, screenText, theta, phi);
        output.drawImage(renderer.view, 0, 0, logicalWidth, logicalHeight);
        orbits(output, phase, true);
        palmLight(output, phase, plottedPoint);
        output.save();
        output.globalCompositeOperation = "soft-light";
        output.globalAlpha = 0.23;
        output.drawImage(texture, 0, 0, logicalWidth, logicalHeight);
        output.restore();
        return output.canvas.toDataURL("image/png").split(",", 2)[1];
    };
}

prepare().catch((error) => { window.renderError = error.stack; });
