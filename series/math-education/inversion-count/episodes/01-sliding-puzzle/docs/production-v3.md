# 第一期 v3：完整视频制作记录

制作日期：2026-10-27。新版全部39段台词已经实际使用晓晓重新配音，并由 `video-maker` 完整渲染。第一期内容边界保持，第二、三期的完整证明未追加到本片。

## 成片与材料

本机交付位置：

```text
D:/workspace/vivhite-analysis-output/math-education/inversion-count/01-sliding-puzzle/production-v3/film.mp4
```

实测 **10分55秒、1920×1080、30fps、19,650帧**，H.264/AAC，49,024,504字节。SHA-256：`2a6ebfe7fa791eea3c8ecc798ef01adfe47fb7bbf01190028d66dd45a8540c8a`。中文字幕已经烧录，另交付同目录 `subtitles.srt`，不附加内嵌字幕轨。

声音为 `edge-tts / zh-CN-XiaoxiaoNeural / +8% / +0Hz / +0%`。人物使用用户给定的原始JPEG占位；没有把图片描述为已经完成的Live2D、口型或表情动画。音色、语速和人物素材通过制作配置替换；新增配音提供方需要实现相同的PCM与词时间契约。

- [完整实测导演稿](director-timed-v3.md)：新版每段真实时间、旁白和动作。
- [稿源导演稿](director-v3.md)、[制作计划](../authoring/production-plan-v3.json)和[全部台词改前改后](dialogue-review-v3.md)。
- [机器可读交付结果](production-result-v3.json)：输入、成片指纹与实际检查范围。

同目录另外保留 `narration.wav`、`timeline.json`、`production-report.json`、`ffprobe.json`、分段编码、TTS缓存、实际编码帧证据、全量机器转写和失败尝试记录。媒体与运行快照在仓库外；历史 `production-v2-cued/` 未覆盖。

## 实际执行

先验证已有制作器能够消费39段v3计划，再把可用JAR和配音worker固定在本期外部目录，避免并发扩展后两期图形时改变第一期执行版本。参考 `Z:/workspace/xar_promo_toolchain` 的提供方隔离、内容哈希缓存、按真实音长排程、失败保留及交付检查方式，未修改该参考工程。

创作前通读完整人格；正式制作前独立复审全部39段实际计划与实际人物图片，分别通过人格一致性、信息披露审核。详细依据保存在私有角色库，公开收据只包含版本绑定与结论。

首次真实晓晓合成后，保护检查发现b05第二、第三动作的起点仅相距0.775458秒，小于制作器要求的0.8秒。保留全部实际配音，将第三动作在“接着是二”的真实词时间后微延迟0.04秒，使相邻间隔成为0.815458秒和0.885917秒，0.75秒滑动得以完整结束。口播、棋盘状态和数学结论未改；修改已回写唯一稿源与计划，并重新完成语义审核。最终计划SHA-256：`6e4888aec3ad4857b62f23d32499ab8c6792c9cdf7c0df906d05463f2fa008b0`。

随后离线复用已校验的39段配音，经RTX 3080 NVENC逐段渲染、合成、响度处理和全片解码，形成上述交付。各期使用独立缓存和输出目录。

## 检查结果与范围

- 所有39段及最终文件的尺寸、帧数和时长一致；19,650帧视频和完整音轨成功解码。整片黑场检测没有发现持续至少0.1秒、至少98%像素落在亮度阈值0.05以下的区间。
- 399个字幕区间逐段对比全部原创旁白，2,661个字母/数字类字符完全一致；旁白全文3,083字符。字幕时间与32次明确动作触发均取自实际Edge词边界，动作没有重叠。
- 14步路线检查全部相邻状态、切段连续性、数字方向、计步器与最终目标；四格巡回、行末两步和五次抽象对换也逐个核对。
- 从最终MP4提取并查看73张证据帧：全部39段中间帧、32个明确动作的完成帧和片头片尾。公式、线对、奇偶读数、字幕与占位人物没有发现错位或异常新增内容。该覆盖不等于逐帧语义审查或人工整片播放。
- 最终编码音轨整片响度为-16.1 LUFS，响度范围2.4 LU，真峰-4.5 dBFS；没有数字削波。以-45 dB阈值检查到39处至少0.7秒的停顿，最长1.164042秒，均对应分段间隔，没有整段静音或旁白缺失。
- 最终编码音轨使用本地 `large-v3-turbo / CPU / int8` 全量机器转写，得到420段，助手已阅读全部转写并逐段核对漏句、关键数字及14步方向；未发现整段缺失。机器识别有“逆序/逆叙”“奇偶/基偶”“矩形/举行”等同音误写，不能据此认定真实发音错误。材料保留在 `encoded-asr/`，不将机器识别与文本复核称为人工回听。

本次不宣称人工全片观看、逐句听音或用户已认可风格相似度。人物仍是可替换的静态图片，当前音轨只有旁白，没有配乐。

## 复现

使用本期最终计划和独立目录；正式配音/渲染前保留人格与实际素材绑定检查。以下命令在仓库根目录执行：

```powershell
$episodeRoot = 'series/math-education/inversion-count/episodes/01-sliding-puzzle'
$out = 'D:/workspace/vivhite-analysis-output/math-education/inversion-count/01-sliding-puzzle/production-v3'
$avatar = 'C:/Users/xenoa/Pictures/718c36bc01a173d0c42c0d1131f67e31055244c7.jpg'
video-maker/.venv/Scripts/python.exe scripts/character_review.py check `
  --episode "$episodeRoot/episode.json" --document "$episodeRoot/authoring/production-plan-v3.json" --asset $avatar
if ($LASTEXITCODE -ne 0) { throw 'Review bindings must pass before production.' }
$env:MAKER_WORKER = "$out/production_worker.snapshot.py"
$env:MAKER_TTS_CACHE = "$out/tts-cache"
$env:MAKER_OFFLINE_TTS = '1'
java -jar "$out/engine.jar" produce "$episodeRoot/authoring/production-plan-v3.json" `
  $out $avatar video-maker/.venv/Scripts/python.exe
```

固定快照用于复现本次执行；后续制作按[通用制作说明](../../../../../../video-maker/docs/production.md)构建当前制作器。文案、声音配置、人格或人物素材变化后，需要新的审核绑定；不能拿当前收据直接放行变更后的输入。
