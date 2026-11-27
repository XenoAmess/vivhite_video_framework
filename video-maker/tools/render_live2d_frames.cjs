const { createServer } = require("node:http");
const { createRequire } = require("node:module");
const { readFile, mkdir, writeFile } = require("node:fs/promises");
const path = require("node:path");

async function main() {
    const [runtimeArg, episodeArg, modelArg, outputArg, chrome, mode] = process.argv.slice(2);
    if (!runtimeArg || !episodeArg || !modelArg || !outputArg || !chrome ||
        !["preview", "frames"].includes(mode)) {
        throw new Error("Usage: node render_live2d_frames.cjs RUNTIME EPISODE MODEL OUTPUT CHROME preview|frames");
    }
    const runtime = path.resolve(runtimeArg);
    const episode = path.resolve(episodeArg);
    const modelHome = path.resolve(modelArg);
    const output = path.resolve(outputArg);
    const { chromium } = createRequire(path.join(runtime, "package.json"))("playwright-core");
    const plan = JSON.parse(await readFile(path.join(episode, "production-plan.json")));
    const routes = new Map([
        ["/pixi.js", path.join(runtime, "node_modules/pixi.js/dist/browser/pixi.min.js")],
        ["/live2d.js", path.join(runtime, "node_modules/pixi-live2d-display/dist/cubism4.min.js")],
        ["/core.js", path.join(runtime, "live2dcubismcore.min.js")],
        ["/artwork.js", path.join(episode, "artwork.js")],
        ["/production-plan.json", path.join(episode, "production-plan.json")],
    ]);
    const mimeTypes = {
        ".js": "text/javascript", ".json": "application/json", ".png": "image/png",
        ".moc3": "application/octet-stream",
    };
    const server = createServer(async (request, response) => {
        try {
            const url = new URL(request.url, "http://localhost");
            if (url.pathname === "/") {
                response.setHeader("Content-Type", "text/html; charset=utf-8");
                response.end('<!doctype html><meta charset="utf-8"><script src="/pixi.js"></script>' +
                    '<script src="/core.js"></script><script src="/live2d.js"></script>' +
                    '<script type="module" src="/artwork.js"></script>');
                return;
            }
            let file = routes.get(url.pathname);
            if (!file && url.pathname.startsWith("/model/")) {
                const requested = path.resolve(modelHome, decodeURIComponent(url.pathname.slice(7)));
                if (requested.startsWith(modelHome + path.sep)) {
                    file = requested;
                }
            }
            if (!file || !mimeTypes[path.extname(file)]) {
                response.writeHead(404).end();
                return;
            }
            response.setHeader("Content-Type", mimeTypes[path.extname(file)]);
            response.end(await readFile(file));
        } catch {
            response.writeHead(404).end();
        }
    });
    await new Promise((resolve, reject) => {
        server.once("error", reject);
        server.listen(0, "127.0.0.1", resolve);
    });
    const origin = `http://127.0.0.1:${server.address().port}`;
    let browser;
    try {
        await mkdir(output, { recursive: true });
        browser = await chromium.launch({
            executablePath: chrome,
            args: ["--use-gl=angle", "--use-angle=swiftshader", "--enable-unsafe-swiftshader"],
        });
        const page = await browser.newPage();
        await page.route("**/*", (route) =>
            route.request().url().startsWith(origin + "/") ? route.continue() : route.abort());
        page.on("pageerror", (error) => process.stderr.write(`${error.stack}\n`));
        await page.goto(origin, { timeout: 60000 });
        await page.waitForFunction(() => window.renderFrame || window.renderError, null, { timeout: 60000 });
        const setup = await page.evaluate(() => ({ error: window.renderError, info: window.renderInfo }));
        if (setup.error) {
            throw new Error(setup.error);
        }
        console.log(JSON.stringify(setup.info));
        const previewFrames = new Set([0, 45, 103, 150, plan.frameCount - 1]);
        for (let frame = 0; frame < plan.frameCount; frame++) {
            const capture = mode === "frames" || previewFrames.has(frame);
            const encoded = await page.evaluate(({ frame, capture }) => window.renderFrame(frame, capture),
                { frame, capture });
            if (capture) {
                const name = `frame-${String(frame).padStart(4, "0")}.png`;
                await writeFile(path.join(output, name), Buffer.from(encoded, "base64"));
            }
            if (mode === "frames" && (frame + 1) % 30 === 0) {
                console.log(`Rendered ${frame + 1}/${plan.frameCount}`);
            }
        }
    } finally {
        await browser?.close();
        server.close();
    }
}

main().catch((error) => {
    process.stderr.write(`${error.stack}\n`);
    process.exitCode = 1;
});
