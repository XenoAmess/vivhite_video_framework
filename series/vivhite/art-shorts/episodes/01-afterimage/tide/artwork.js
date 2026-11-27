const WIDTH = 1408;
const HEIGHT = 512;
const TAU = 2 * Math.PI;
const SERIF = '"Noto Serif SC", SimSun, serif';

const matteVertex = `#version 300 es
out vec2 uv;
void main() {
    vec2 p = vec2(gl_VertexID == 1 ? 3.0 : -1.0, gl_VertexID == 2 ? 3.0 : -1.0);
    uv = vec2((p.x + 1.0) * 0.5, (1.0 - p.y) * 0.5);
    gl_Position = vec4(p, 0.0, 1.0);
}`;

const matteFragment = `#version 300 es
precision highp float;
in vec2 uv;
out vec4 outColor;
uniform sampler2D overlay;
uniform sampler2D portrait;
uniform vec3 paper, ink, tint, accent;
uniform vec4 box;
uniform vec2 head, focal;
uniform vec4 music;
uniform vec3 motion;
uniform float clock, gesture, exposure;
uniform int layer;

float hash(vec2 p) {
    vec3 v = fract(vec3(p.xyx) * 0.1031);
    v += dot(v, v.yzx + 33.33);
    return fract((v.x + v.y) * v.z);
}

void main() {
    vec2 p = uv * vec2(1408.0, 512.0);
    if (layer == 1) {
        vec2 tex = (p - box.xy) / box.zw;
        float extremes = smoothstep(0.12, 0.37, abs(tex.x - 0.49));
        tex.y -= (0.012 * motion.x + 0.028 * motion.y * extremes)
                 * (0.35 + 0.65 * smoothstep(0.20, 0.85, tex.y));
        tex.x -= 0.012 * gesture * smoothstep(0.27, 0.55, abs(tex.x - 0.50))
                 * (1.0 - smoothstep(0.34, 0.85, tex.y)) * sign(tex.x - 0.50);
        if (any(lessThan(tex, vec2(0.0))) || any(greaterThan(tex, vec2(1.0)))) discard;
        vec4 image = texture(portrait, tex);
        float highlight = exp(-length((p-focal) / vec2(243.0, 170.0)) * 1.9);
        vec3 reflected = mix(image.rgb, accent, highlight * (0.035 + 0.073 * music.z));
        reflected = mix(reflected, tint * 0.41, 0.12 * motion.z);
        outColor = vec4(reflected, image.a * exposure);
        return;
    }
    float fiber = hash(floor(p * 1.53)) - 0.5;
    float edge = min(min(p.x - 67.0 + 0.105*p.y, 1359.0 - p.x - 0.072*p.y),
                     min(p.y - 27.0 + 0.011*p.x, 484.0 - p.y + 0.009*p.x));
    edge += 1.2 * sin(p.x * 0.53 + p.y * 0.37) + 3.1 * (hash(floor(p / 3.4)) - 0.5);
    vec3 outside = paper * (0.91 + 0.040 * fiber + 0.045*sin(uv.x*3.0));
    outside *= 1.0 - 0.09 * exp(-abs(edge + 2.0) * 0.20);
    vec2 rel = (p - head) * vec2(0.0035, 0.0048);
    rel = mat2(0.94, 0.34, -0.34, 0.94) * rel;
    float r = length(rel);
    float fan = 0.5 + 0.5*sin(15.4*rel.x + 8.0*rel.y + 4.5*sin(6.2*rel.y-clock*0.29)
                         + 2.1*sin(rel.x*5.0 + clock*0.18));
    float foam = pow(fan, 5.0) * (0.037 + 0.105 * music.w);
    float moon = 1.0 - smoothstep(1.064, 1.09, r);
    float radial = exp(-1.25*r*r);
    float rings = pow(0.5 + 0.5*cos(49.0*r), 31.0) * 0.115 * moon;
    vec3 inner = ink + tint * (0.052 + 0.043*sin(uv.x*5.2 + uv.y));
    inner += moon * mix(tint * 0.25, paper * 0.70, radial);
    inner = mix(inner, ink, rings);
    inner += tint * foam * exp(-0.49*r*r);
    inner += (fiber * 0.030 + 0.012*sin(p.y*0.082+p.x*0.07)) * (0.65 + radial);
    vec3 bg = mix(outside, inner, smoothstep(-0.7, 0.7, edge));
    vec4 text = texture(overlay, uv);
    bg = mix(bg, text.rgb, text.a);
    float water = pow(0.5 + 0.5*cos(uv.x*10.2 + uv.y*13.0 + 2.8*sin(uv.y*4.0-clock*0.14)), 4.0);
    bg += tint * 0.027 * water * music.y;
    outColor = vec4(mix(vec3(0.040, 0.074, 0.115), bg, exposure), 1.0);
}`;

const lineVertex = `#version 300 es
in vec2 point;
uniform float size;
void main() {
    gl_Position = vec4(point.x / 704.0 - 1.0, 1.0 - point.y / 256.0, 0.0, 1.0);
    gl_PointSize = size;
}`;

const lineFragment = `#version 300 es
precision highp float;
out vec4 outColor;
uniform vec4 color;
uniform int dots;
void main() {
    float a = color.a;
    if (dots == 1) {
        float r = length(gl_PointCoord - 0.5) * 2.0;
        a *= exp(-r*r*4.5) * (1.0 - smoothstep(0.81, 1.0, r));
    }
    outColor = vec4(color.rgb, a);
}`;

function rgb(hex) {
    return [1, 3, 5].map((i) => parseInt(hex.slice(i, i + 2), 16) / 255);
}

function smooth(from, to, value) {
    const t = Math.min(1, Math.max(0, (value - from) / (to - from)));
    return t * t * (3 - 2 * t);
}

function canvasAt(width, height) {
    const canvas = document.createElement("canvas");
    canvas.width = width;
    canvas.height = height;
    return canvas;
}

function text(ctx, value, x, y, size, color, font, spacing = 0, weight = 400) {
    ctx.font = weight + " " + size + "px " + font;
    ctx.letterSpacing = spacing + "px";
    ctx.fillStyle = color;
    ctx.fillText(value, x, y);
}

function makeLine(ctx, x, y, endX, endY, color, width) {
    ctx.beginPath();
    ctx.moveTo(x, y);
    ctx.lineTo(endX, endY);
    ctx.strokeStyle = color;
    ctx.lineWidth = width;
    ctx.stroke();
}

function composeLabel(plan, chapter) {
    const canvas = canvasAt(plan.width, plan.height);
    const ctx = canvas.getContext("2d");
    ctx.scale(plan.width / WIDTH, plan.height / HEIGHT);
    const right = chapter.side === "right";
    const tx = right ? 133 : 1027;
    const y = 113;
    const [xg, yg, gx, gy] = chapter.plot;
    const panelX = Math.max(56, xg - gx - 28);
    const panelW = Math.min(WIDTH - panelX - 56, gx * 2 + 56);
    ctx.fillStyle = "#10142565";
    ctx.fillRect(panelX, yg - gy - 30, panelW, gy * 2 + 73);
    ctx.strokeStyle = chapter.light + "50";
    ctx.lineWidth = 0.7;
    ctx.strokeRect(panelX, yg - gy - 30, panelW, gy * 2 + 73);
    for (let x = xg - gx; x <= xg + gx; x += 13) {
        makeLine(ctx, x, yg - gy, x, yg + gy, chapter.light + "23", 0.48);
    }
    for (let row = yg - gy; row <= yg + gy; row += 13) {
        makeLine(ctx, xg - gx, row, xg + gx, row, chapter.light + "23", 0.48);
    }
    makeLine(ctx, xg - gx - 5, yg, xg + gx + 5, yg, chapter.light + "87", 0.68);
    makeLine(ctx, xg, yg - gy - 4, xg, yg + gy + 4, chapter.light + "87", 0.68);
    text(ctx, "x", xg + gx - 7, yg - 6, 12, chapter.light, "Consolas");
    text(ctx, "y", xg + 5, yg - gy + 10, 12, chapter.light, "Consolas");
    text(ctx, plan.screenText.plot, panelX + 13, yg - gy - 10, 12, "#ecedf7", SERIF, 1, 700);
    text(ctx, plan.screenText.equations[0], panelX + 13, yg + gy + 25, 12, chapter.light, "Consolas");
    text(ctx, plan.screenText.equations[1], panelX + panelW - 100, yg + gy + 25, 12, chapter.accent, "Consolas");

    ctx.fillStyle = chapter.accent;
    ctx.fillRect(tx, y - 6, 18, 2);
    text(ctx, plan.screenText.character, tx + 25, y, 14, "#e6ebf2", SERIF, 1.8);
    text(ctx, plan.screenText.title, tx - 7, y + 95, 92, "#f0ebe6", SERIF, 8, 800);
    makeLine(ctx, tx, y + 115, tx + 241, y + 115, chapter.light + "a0", 0.75);
    text(ctx, plan.screenText.subtitle + "　/　" + chapter.title, tx, y + 148, 21, chapter.accent, SERIF, 2.3);
    text(ctx, plan.audio.title, tx, y + 180, 11, "#e3e6f0", SERIF, 0.6);

    const waveX = tx - 5;
    const waveY = 366;
    ctx.fillStyle = "#0c1423a0";
    ctx.fillRect(waveX, waveY, 249, 73);
    ctx.strokeStyle = chapter.light + "51";
    ctx.strokeRect(waveX, waveY, 249, 73);
    ctx.lineWidth = 0.65;
    text(ctx, "分量　/　θ", waveX + 10, waveY + 16, 10, "#e7e9f0", SERIF);
    text(ctx, "x", waveX + 205, waveY + 16, 11, chapter.light, "Consolas");
    text(ctx, "y", waveX + 229, waveY + 16, 11, chapter.accent, "Consolas");
    makeLine(ctx, waveX + 10, waveY + 41, waveX + 239, waveY + 41, "#e4dff448", 0.55);
    for (const [a, b] of [[43, 62], [1366, 450], [47, 452], [1363, 63]]) {
        makeLine(ctx, a - 6, b, a + 6, b, "#24395273", 0.65);
        makeLine(ctx, a, b - 6, a, b + 6, "#24395273", 0.65);
    }
    return { canvas, wave: [waveX + 10, waveY + 41, 229] };
}

function program(gl, vertex, fragment, names) {
    const id = gl.createProgram();
    for (const [kind, source] of [[gl.VERTEX_SHADER, vertex], [gl.FRAGMENT_SHADER, fragment]]) {
        const shader = gl.createShader(kind);
        gl.shaderSource(shader, source);
        gl.compileShader(shader);
        if (!gl.getShaderParameter(shader, gl.COMPILE_STATUS)) {
            throw new Error(gl.getShaderInfoLog(shader));
        }
        gl.attachShader(id, shader);
    }
    gl.linkProgram(id);
    if (!gl.getProgramParameter(id, gl.LINK_STATUS)) {
        throw new Error(gl.getProgramInfoLog(id));
    }
    return { id, uniforms: Object.fromEntries(names.map((name) => [name, gl.getUniformLocation(id, name)])) };
}

function texture(gl, source) {
    const image = gl.createTexture();
    gl.bindTexture(gl.TEXTURE_2D, image);
    gl.texParameteri(gl.TEXTURE_2D, gl.TEXTURE_MIN_FILTER, gl.LINEAR);
    gl.texParameteri(gl.TEXTURE_2D, gl.TEXTURE_MAG_FILTER, gl.LINEAR);
    gl.texParameteri(gl.TEXTURE_2D, gl.TEXTURE_WRAP_S, gl.CLAMP_TO_EDGE);
    gl.texParameteri(gl.TEXTURE_2D, gl.TEXTURE_WRAP_T, gl.CLAMP_TO_EDGE);
    gl.texImage2D(gl.TEXTURE_2D, 0, gl.RGBA, gl.RGBA, gl.UNSIGNED_BYTE, source);
    return image;
}

function loadPortrait(spec) {
    const image = new Image();
    image.src = "/" + spec.file;
    return image.decode().then(() => image);
}

function makeStroke(gl, depth) {
    const buffer = gl.createBuffer();
    const attribute = gl.getAttribLocation(depth.id, "point");
    const vertices = new Float32Array(680);
    const u = depth.uniforms;
    return (mode, count, point, color, alpha, size = 1) => {
        for (let i = 0; i < count; i++) {
            const [x, y] = point(i / Math.max(1, count - 1), i);
            vertices[i * 2] = x;
            vertices[i * 2 + 1] = y;
        }
        gl.useProgram(depth.id);
        gl.bindBuffer(gl.ARRAY_BUFFER, buffer);
        gl.bufferData(gl.ARRAY_BUFFER, vertices.subarray(0, count * 2), gl.DYNAMIC_DRAW);
        gl.enableVertexAttribArray(attribute);
        gl.vertexAttribPointer(attribute, 2, gl.FLOAT, false, 0, 0);
        gl.uniform1i(u.dots, mode === gl.POINTS ? 1 : 0);
        gl.uniform1f(u.size, size);
        gl.uniform4f(u.color, color[0], color[1], color[2], alpha);
        gl.drawArrays(mode, 0, count);
    };
}

function insideBezier(a, b, c, d, t) {
    const u = 1 - t;
    return u*u*u*a + 3*u*u*t*b + 3*u*t*t*c + t*t*t*d;
}

async function prepare() {
    const plan = await (await fetch("/production-plan.json")).json();
    const featureResponse = await fetch("/features.f32");
    const features = new Float32Array(await featureResponse.arrayBuffer());
    if (features.length !== plan.frameCount * 5) {
        throw new Error("Sound feature grid does not match the picture timeline.");
    }
    await document.fonts.load("800 92px " + SERIF, plan.screenText.title);
    const canvas = canvasAt(plan.width, plan.height);
    const gl = canvas.getContext("webgl2", { alpha: false, antialias: true, preserveDrawingBuffer: true });
    if (!gl) {
        throw new Error("WebGL 2 is required for this artwork.");
    }
    const rendererInfo = gl.getExtension("WEBGL_debug_renderer_info");
    gl.viewport(0, 0, plan.width, plan.height);
    gl.enable(gl.BLEND);
    gl.blendFunc(gl.SRC_ALPHA, gl.ONE_MINUS_SRC_ALPHA);
    const matte = program(gl, matteVertex, matteFragment,
        ["overlay", "portrait", "paper", "ink", "tint", "accent", "box", "head", "focal",
            "music", "motion", "clock", "gesture", "exposure", "layer"]);
    const geometry = program(gl, lineVertex, lineFragment, ["color", "size", "dots"]);
    const draw = makeStroke(gl, geometry);
    const loaded = Object.fromEntries(await Promise.all(Object.entries(plan.portraits).map(async ([key, spec]) => {
        const source = await loadPortrait(spec);
        return [key, { ...spec, ratio: source.height / source.width, texture: texture(gl, source) }];
    })));
    const scenes = plan.chapters.map((chapter) => {
        const { canvas: layout, wave } = composeLabel(plan, chapter);
        return { chapter, wave, titleTexture: texture(gl, layout), actor: loaded[chapter.pose],
            ink: rgb(chapter.ink), paper: rgb(chapter.paper), tint: rgb(chapter.light), accent: rgb(chapter.accent) };
    });
    const particles = Array.from({ length: 91 }, (_, i) => [
        81 + (i * 777.37) % 1257, 29 + (i * 153.39) % 432, i * 2.39996,
    ]);
    const nominalPhrase = plan.audio.phraseSeconds;

    function render(sceneIndex, index) {
        const { chapter, actor, titleTexture, tint, accent, paper, ink, wave } = scenes[sceneIndex];
        const t = index / plan.fps;
        const dt = (index - chapter.startFrame) / plan.fps;
        const remaining = (chapter.endFrame - index - 1) / plan.fps;
        const exposure = smooth(0, 2.5, dt) * smooth(0, 2.9, remaining);
        const style = sceneIndex * 0.73;
        const phase = t * TAU / nominalPhrase;
        const drift = 0.55 * Math.sin(t * 0.051 + style) + 0.45 * Math.sin(phase * 0.68);
        const offset = index * 5;
        const [bass, middle, clear, high, shimmer] = features.subarray(offset, offset + 5);
        const theta = (TAU + (phase + 0.46 * Math.sin(phase) + 0.19 * Math.sin(t * 0.088 + style)) % TAU) % TAU;
        const phi = 0.66 + 0.53 * Math.sin(phase * 0.29 + style) + 0.14 * middle;
        const [px, py, size] = chapter.portrait;
        const dx = px + 4.8 * Math.sin(phase * 0.56 + style);
        const dy = py + 5.9 * drift;
        const width = size * (1 + 0.014 * Math.sin(phase * 0.41 + style));
        const height = width * actor.ratio;
        const focus = [dx + width * actor.tip[0], dy + height * actor.tip[1]];
        const [cx, cy, rx, ry] = chapter.plot;
        const flip = chapter.side === "right" ? 1 : -1;
        const curve = (a, shift = 0) => [cx + rx * Math.sin(3*a + phi + shift), cy - ry * Math.sin(2*a)];
        const marker = curve(theta);

        const uniforms = matte.uniforms;
        gl.useProgram(matte.id);
        gl.activeTexture(gl.TEXTURE0);
        gl.bindTexture(gl.TEXTURE_2D, titleTexture);
        gl.uniform1i(uniforms.overlay, 0);
        gl.activeTexture(gl.TEXTURE1);
        gl.bindTexture(gl.TEXTURE_2D, actor.texture);
        gl.uniform1i(uniforms.portrait, 1);
        gl.uniform3fv(uniforms.paper, paper);
        gl.uniform3fv(uniforms.ink, ink);
        gl.uniform3fv(uniforms.tint, tint);
        gl.uniform3fv(uniforms.accent, accent);
        gl.uniform4f(uniforms.box, dx, dy, width, height);
        gl.uniform2f(uniforms.head, dx + width * actor.head[0], dy + height * actor.head[1] + 63);
        gl.uniform2fv(uniforms.focal, focus);
        gl.uniform4f(uniforms.music, bass, middle, clear, high);
        gl.uniform1f(uniforms.clock, t);
        gl.uniform1f(uniforms.gesture, Math.sin(phase * 0.71 + style));
        gl.uniform3f(uniforms.motion, drift, Math.sin(phase * 0.88 + style), 1 - middle);
        gl.uniform1f(uniforms.exposure, exposure);
        gl.uniform1i(uniforms.layer, 0);
        gl.drawArrays(gl.TRIANGLES, 0, 3);

        for (const [shift, color, a] of [[-0.13, accent, 0.29], [0.13, tint, 0.36], [0, tint, 0.88]]) {
            draw(gl.LINE_STRIP, 245, (z) => curve(TAU*z, shift), color, a * exposure);
        }
        draw(gl.LINE_STRIP, 38, (z) => curve(theta + (z - 1) * 0.56), accent, (0.67 + 0.24 * clear) * exposure);
        const [wx, wy, ww] = wave;
        draw(gl.LINE_STRIP, 94, (a) => [wx + ww*a, wy - 15 * Math.sin(3*TAU*a+phi)], tint, 0.86 * exposure);
        draw(gl.LINE_STRIP, 94, (a) => [wx + ww*a, wy - 15 * Math.sin(2*TAU*a)], accent, 0.86 * exposure);
        const cursor = wx + theta / TAU * ww;
        draw(gl.LINES, 2, (a) => [cursor, wy - 16 + a * 34], paper, 0.52 * exposure);
        draw(gl.POINTS, 2, (a) => [cursor, wy - 15 * (a ? Math.sin(2*theta) : Math.sin(3*theta+phi))],
            paper, exposure, 8);
        draw(gl.POINTS, particles.length, (a, i) => {
            const [x, y, seed] = particles[i];
            return [x + 13*Math.sin(seed + t*0.12), 26 + (y + t * (2 + 0.32 * (i%8))) % 450];
        }, tint, (0.26 + 0.38 * shimmer) * exposure, 4.8);

        gl.useProgram(matte.id);
        gl.uniform1i(uniforms.layer, 1);
        gl.drawArrays(gl.TRIANGLES, 0, 3);

        for (let i = 0; i < 5; i++) {
            const a = i - 2;
            const sw = 17 * Math.sin(phase * 0.52 + style + 0.25 * i);
            draw(gl.LINE_STRIP, 94, (z) => [
                insideBezier(705 - flip*320, 705 - flip*20, focus[0]+flip*15, focus[0]+flip*(11+4*a), z),
                insideBezier(429 + a*9, 565 + a*13, 258 + sw + a*12, focus[1]+2+a*4, z),
            ], i % 2 ? tint : accent, (0.33 + 0.21 * bass + (i === 2 ? 0.15 : 0)) * exposure);
        }
        for (const [color, opacity, size] of [
            [tint, 0.58, 52 + 30*clear], [accent, 0.83, 22 + 10*middle], [[1,0.97,0.86], 1, 9 + 7*high],
        ]) {
            draw(gl.POINTS, 1, () => marker, color, opacity*exposure, size);
        }
        const [sx, sy] = marker;
        const length = 6 + 8 * clear;
        draw(gl.LINES, 2, (z) => [sx - length + 2*length*z, sy], accent, 0.9*exposure);
        draw(gl.LINES, 2, (z) => [sx, sy - 0.62*length + 1.24*length*z], accent, 0.9*exposure);
    }

    window.tide = { canvas, render, plan, renderer: rendererInfo &&
        gl.getParameter(rendererInfo.UNMASKED_RENDERER_WEBGL) };
}

prepare().catch((error) => { window.tideError = error.stack; });
