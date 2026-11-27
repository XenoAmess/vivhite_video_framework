const { createServer } = require("node:http");
const { createRequire } = require("node:module");
const { mkdir, open, readFile, rename, writeFile } = require("node:fs/promises");
const path = require("node:path");

async function main() {
    const [runtime, input, output, chrome, mode] = process.argv.slice(2);
    if (!runtime || !input || !output || !chrome || !["preview", "render"].includes(mode)) {
        throw new Error("Usage: node render_music_visualizer.cjs RUNTIME INPUT OUTPUT CHROME preview|render");
    }
    const { chromium } = createRequire(path.resolve(runtime, "package.json"))("playwright-core");
    const plan = JSON.parse(await readFile(path.join(input, "production-plan.json")));
    const routes = new Map([
        ["/", ["text/html", Buffer.from('<!doctype html><meta charset="utf-8"><script type="module" src="/artwork.js"></script>')]],
        ...[["production-plan.json", "application/json"], ["artwork.js", "text/javascript"],
            ["features.f32", "application/octet-stream"],
            ...Object.values(plan.portraits).map(({ file }) => [file, "image/png"]),
        ].map(([file, contentType]) => ["/" + file, [contentType, path.join(input, file)]]),
    ]);
    let active;
    const server = createServer(async (request, response) => {
        try {
            if (request.method === "POST" && request.url === "/packets" && active) {
                for await (const bytes of request) {
                    await active.writeFile(bytes);
                }
                response.writeHead(204).end();
                return;
            }
            const entry = routes.get(request.url);
            if (!entry || request.method !== "GET") {
                response.writeHead(404).end();
                return;
            }
            const [contentType, source] = entry;
            response.setHeader("Content-Type", contentType);
            response.end(Buffer.isBuffer(source) ? source : await readFile(source));
        } catch (error) {
            console.error(error.message);
            response.writeHead(500).end();
        }
    });
    await new Promise((resolve, reject) => {
        server.once("error", reject);
        server.listen(0, "127.0.0.1", resolve);
    });
    const origin = "http://127.0.0.1:" + server.address().port;
    let browser;
    try {
        browser = await chromium.launch({ executablePath: chrome });
        const page = await browser.newPage();
        await page.route("**/*", (route) => route.request().url().startsWith(origin + "/")
            ? route.continue() : route.abort());
        page.on("pageerror", (error) => process.stderr.write(error.stack + "\n"));
        page.on("console", (message) => {
            if (message.text().startsWith("Render ")) console.log(message.text());
        });
        await page.goto(origin, { timeout: 60000 });
        await page.waitForFunction(() => window.tide || window.tideError, null, { timeout: 60000 });
        const boot = await page.evaluate(() => ({ error: window.tideError, gpu: window.tide?.renderer }));
        if (boot.error) {
            throw new Error(boot.error);
        }
        console.log(JSON.stringify(boot));
        if (mode === "preview") {
            for (let i = 0; i < plan.chapters.length; i++) {
                const png = await page.evaluate((index) => {
                    const { canvas, render, plan: current } = window.tide;
                    const scene = current.chapters[index];
                    const frame = scene.startFrame + Math.round((scene.endFrame - scene.startFrame) * 0.27);
                    render(index, frame);
                    return canvas.toDataURL("image/png").split(",", 2)[1];
                }, i);
                await writeFile(path.join(output, "preview-" + (i + 1) + ".png"), Buffer.from(png, "base64"));
            }
            return;
        }
        const segments = path.join(output, "segments");
        await mkdir(segments);
        for (let i = 0; i < plan.chapters.length; i++) {
            const stem = String(i).padStart(2, "0");
            const part = path.join(segments, stem + ".part");
            active = await open(part, "wx");
            let stats;
            try {
                stats = await page.evaluate(encodeChapter, i);
            } finally {
                await active.close();
                active = undefined;
            }
            await rename(part, path.join(segments, stem + ".h264"));
            console.log(JSON.stringify({ chapter: plan.chapters[i].id, ...stats }));
        }
    } finally {
        await browser?.close();
        server.close();
    }
}

async function encodeChapter(index) {
    const { canvas, render, plan } = window.tide;
    const chapter = plan.chapters[index];
    const config = {
        codec: "avc1.4d0033", width: canvas.width, height: canvas.height, framerate: plan.fps,
        latencyMode: "realtime", hardwareAcceleration: "prefer-hardware",
        bitrate: plan.bitrate, avc: { format: "annexb" },
    };
    if (!(await VideoEncoder.isConfigSupported(config)).supported) {
        throw new Error("Chromium does not support the required H.264 encoder configuration.");
    }
    let error;
    let packets = [];
    let pendingBytes = 0;
    let bytes = 0;
    let sentFrames = 0;
    let lastTimestamp = -1;
    const encoder = new VideoEncoder({
        output(chunk) {
            if (chunk.timestamp <= lastTimestamp) error = new Error("H.264 packets are out of presentation order.");
            lastTimestamp = chunk.timestamp;
            sentFrames++;
            const packet = new Uint8Array(chunk.byteLength);
            chunk.copyTo(packet);
            packets.push(packet);
            pendingBytes += packet.length;
            bytes += packet.length;
        },
        error(failure) { error = failure; },
    });
    async function send() {
        if (!pendingBytes) return;
        const payload = new Blob(packets);
        packets = [];
        pendingBytes = 0;
        const response = await fetch("/packets", { method: "POST", body: payload });
        if (!response.ok) throw new Error("Could not write H.264 packets.");
    }
    const began = performance.now();
    encoder.configure(config);
    try {
        for (let frame = chapter.startFrame; frame < chapter.endFrame; frame++) {
            while (encoder.encodeQueueSize > 10 && !error) {
                await new Promise((resolve) => setTimeout(resolve, 0));
            }
            if (error) throw error;
            if (pendingBytes >= 3_000_000) await send();
            render(index, frame);
            const offset = frame - chapter.startFrame;
            const timestamp = Math.round(offset * 1_000_000 / plan.fps);
            const duration = Math.round((offset + 1) * 1_000_000 / plan.fps) - timestamp;
            const picture = new VideoFrame(canvas, { timestamp, duration });
            try {
                encoder.encode(picture, { keyFrame: offset % (2 * plan.fps) === 0 });
            } finally {
                picture.close();
            }
            if (offset > 0 && offset % 3000 === 0) {
                console.log("Render " + chapter.id + " " + offset + "/" + (chapter.endFrame - chapter.startFrame));
            }
        }
        await encoder.flush();
        await send();
        if (error) throw error;
        if (sentFrames !== chapter.endFrame - chapter.startFrame) {
            throw new Error("Encoder dropped frames in " + chapter.id + ": " + sentFrames);
        }
        return { frames: sentFrames, bytes, seconds: (performance.now() - began) / 1000 };
    } finally {
        if (encoder.state !== "closed") encoder.close();
    }
}

main().catch((error) => {
    process.stderr.write(error.stack + "\n");
    process.exitCode = 1;
});
