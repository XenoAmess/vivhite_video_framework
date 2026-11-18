# 本地4K编码计时

2026-11-18，使用已通过助手源片画面审阅的S05原生3840×2160视频做5秒技术编码，保留原始文件和校准结果。该片段不是正式交付，也未授予成片审核结论。

实际源片SHA-256：`62aa1dab5b48ad7093b294a442c595418e427f3389918065c1c487bd12b3f318`。采用`fps=30`、`libx264`、`medium`、CRF 18、`yuv420p`，混入现有配乐的前5秒，AAC 256k／48kHz。输出3840×2160、150帧、音视频均为5秒，完整解码通过。

本机实际编码耗时**6.312秒**。205秒按相同负荷线性折算约**258.79秒／4.31分钟**，但本次不含字幕、片尾淡出和其他镜头的不同画面复杂度；这不是全片实测或交付保证。全部分段转30fps、装配、最终解码、逐帧画面审查和发布另计。局域网4K模型生成每个5秒源片约77分钟，当前耗时主要来自该阶段，不能把本地编码计时套到模型生成上。

文件在仓库外`production-v11-native-4k-001/encoding-calibration/S05-medium-001/`：

- `technical-encode.mp4`：真实可播放的技术校准片段。
- `receipt.json`：实际编码耗时、输入／输出哈希、完整命令和范围限制。
- `encoder.log`、`decode.log`：编码与全量解码日志。

在已有FFmpeg和同一运行目录的机器上，可按以下命令复测；给输出使用新文件名，`-n`保证已有结果不被覆盖：

```powershell
$calibrationRun = 'D:/workspace/vivhite-analysis-output/vivhite/autumn-journey/production-v11-native-4k-001'
Measure-Command {
    ffmpeg -n -v error -i "$calibrationRun/sources/S05.mp4" -i "$calibrationRun/soundtrack.wav" `
        -map 0:v:0 -map 1:a:0 -vf fps=30 -frames:v 150 -t 5 `
        -c:v libx264 -crf 18 -preset medium -pix_fmt yuv420p `
        -c:a aac -b:a 256k -ar 48000 -movflags +faststart "$calibrationRun/encoding-calibration/new-test.mp4"
}
```

计时不包含模型再生成，不改变人物动作、蝴蝶节奏或任何镜头时长，也不替代正式合成前的实际素材绑定检查和成片审阅。
