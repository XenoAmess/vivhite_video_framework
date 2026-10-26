# 从制作计划到完整视频

`produce` 已实现实际配音、动画渲染与 MP4 导出。Java 负责计划校验、数学图形、资源与进程生命周期、分段编码、复用缓存、合成和整片解码检查；Python worker 只负责在线 Edge TTS、配音缓存、字幕时间和 PCM 拼接。案例适配器负责本例文案与叙事，不写在通用 CLI 中。两个 Maven 模块仍不互相依赖。

## 环境与运行

需要 JDK 21、Python 3.12、FFmpeg/ffprobe 和可显示中文的字体。本机使用 Windows 自带 `Microsoft YaHei UI`；其他系统需安装合适字体并修改计划的 `fontFamily`。不分发字体文件。默认编码器 `libx264` 可在普通 CPU 上使用；本次成片选用 RTX 3080 的 `h264_nvenc`。

```powershell
uv venv --python 3.12 video-maker/.venv
uv pip install --python video-maker/.venv/Scripts/python.exe -r video-maker/tools/requirements-lock.txt
.\mvnw.cmd -pl video-maker -am verify

# 同机复用已有分析报告和数学数据；生成完整视频
.\scripts\produce-puzzle-video.ps1 -VideoCodec h264_nvenc

# 更换声音、语速、人物；新素材及音色进入缓存键
.\scripts\produce-puzzle-video.ps1 -Voice zh-CN-XiaoxiaoNeural -Rate '+8%' `
  -Presenter C:/assets/presenter.webm -OutputDirectory D:/renders/puzzle-next
```

本例脚本从已有案例分析生成计划，核对源视频指纹及知识点覆盖，不会重新下载或识别原视频。仅重建旧 v1 导演稿的脚本 `run-puzzle-case.ps1` 与这里的制作入口分开。

直接消费其他已编写计划时，在仓库根目录执行：

```powershell
$jar = 'video-maker/target/video-maker-0.1.0-SNAPSHOT.jar'
$plan = 'video-maker/examples/puzzle-restyle/production-plan-v2.json'
$avatar = 'C:/Users/xenoa/Pictures/718c36bc01a173d0c42c0d1131f67e31055244c7.jpg'
java -jar $jar validate-production $plan
java -jar $jar preview $plan D:/renders/puzzle/preview $avatar
java -jar $jar produce $plan D:/renders/puzzle $avatar video-maker/.venv/Scripts/python.exe
```

现有 `render ANALYSIS DIRECTOR OUT` 仍只导出旧导演契约的文档；实际制作命令是 `produce`。`preview` 输出每段一张技术预览，不能当作已生成完整视频。

## 计划契约与动态配置

计划版本是 `vivhite-production-1`。顶层有标题、宽高、fps、字体、编码器、`voice` 和 `beats`。每个 beat 包含完整旁白、章节、标题、动作说明、图形类型、数学状态序列、公式、次层注释及角色提示。案例另外保留知识点、来源语音段和风格机制引用；这些引用由案例适配器与已验证报告绑定。通用制作器验证结构和数学动作，不把引用存在当作语义分析通过。

`voice.provider/name/rate/pitch/volume` 与画面分离。本次是 `edge-tts / zh-CN-XiaoxiaoNeural / +8% / +0Hz / +0%`；不会模仿参考作者声线。现在在线提供方只实现 Edge，新增提供方时在独立配音 worker 增加适配即可，Java 图形层不依赖 Edge SDK。切换提供方需要实现相同的 PCM 与词边界输出，不能仅换一个未实现的提供方名字。

Edge 是联网服务，会接收新片旁白与声音参数；不上传人物图、原视频或分析证据。依赖固定 `edge-tts 7.3.1`；参考项目的 7.2.8 在本机真实请求返回 403，上游后续版本已修复协议变化，见 [上游 #490](https://github.com/rany2/edge-tts/issues/490)。服务端可能变化，缓存中保存实际音频、词边界及哈希；不能保证未来重新联网合成逐字节一致。

人物作为独立 `PresenterAsset` 加载。JPEG/PNG 使用原图占位，带轻微出场移动、呼吸位移、提示气泡和指示线；没有从单张图生成口型。MP4/MOV/WebM 会以 12fps 解码最长 120 秒，保持比例并循环显示，便于消费后续 Live2D/其他工具已渲染的形象视频。**目前不直接驱动 Live2D 模型，也未实现口型和表情参数映射**。这些都可继续添加在人物层，不必重写棋盘图形。

## 图形与排程

目前提供棋盘滑动、数组连线/交叉计数、抽象对换、棋盘染色与奇偶读数、四格可达环、搜索层展开、路径回放和片尾图层。它们是当前数学图形后端的有限类型集合；新数学主题需要增加图形 primitive 或新的后端，不是输入任意旁白就能自动得到任意动画。

棋盘状态包含 `0`，每一步都检查是否仅把相邻滑块滑入空格；抽象对换单独标记和校验。显示的逆序数、空格坐标与标记均从数组实时计算。状态图从真实邻居生成，四格环由合法移动遍历生成。输入示例的十四步路线消费分析器已经验证的数据，制作器另用 BFS 核对步数。

每段配音得到真实 PCM 长度后，向上取整到完整视频帧，并增加约 0.42 秒阅读间隔。48kHz 可被支持的 fps 整除，整片音轨按帧数精确补零拼接，避免分段累计漂移。字幕使用服务词边界，匹配文本时恢复原创文案标点；不凭字数估计字幕时间。

关键动作可声明 `moveCues: [{phrase, delay}]`，动作时间绑定旁白中该短语的实际词边界，单步用 0.75 秒完成后保留结果。缺短语、边界文本不匹配、动作重叠或超出段长都会失败。连线可用 `focusPairs: [{phrase, delay, pair}]`，在实际讲到某一对数字时高亮它们，也可展示不交叉的对照。本例四格绕圈、行末归位、五次对换、部分路线及关键连线使用词时间；其余动画按本段实际时长均匀排程，不声称全片所有视觉细节都有音素级绑定。

## 产物、恢复与检查

```text
production-plan.json          本次实际输入快照
timeline.json                 实测音频长度、逐段帧区间、字幕及关键动作时间
narration.wav                 48kHz 单声道合成音轨
subtitles.srt                 全片外置中文字幕
segments/                     H.264 分段及带哈希的缓存收据
segments.ffconcat             合成清单
review-frames/                每段一张实际排程对应帧
director-timed.md             按真实时间导出的完整导演稿
film.mp4                      H.264/AAC；已烧中文字幕，SRT另行交付
ffprobe.json                  实际成片媒体信息
production-report.json        成片 SHA-256、帧数、时长、技术检查状态
attempts/                     每次尝试的成功/失败收据
tts-cache/                    配音、请求参数、词时间、内容哈希
```

设置 `MAKER_TTS_CACHE` 可跨输出目录复用已校验配音；`MAKER_OFFLINE_TTS=1` 只使用缓存，缺失时失败。`MAKER_PYTHON`、`MAKER_WORKER`、`FFMPEG`、`FFPROBE` 可覆盖可执行文件/worker 路径。脚本有相应的 `-TtsCacheDirectory`、`-OfflineTts` 参数。

重复执行会校验分段缓存的输入键和输出 SHA-256，复用匹配片段；不把不匹配文件当作完成。同一次制作中的相同旁白共用一个正在执行的配音请求，避免重复缓存写入。失败留下 partial 文件与尝试记录，最终文件只在合成与检查成功后替换。外部进程不用 shell，使用超时并在取消或失败时清理子进程。当前没有跨制作进程的文件锁，应串行使用同一输出目录或共享配音缓存；需要同时制作时使用独立缓存。

输出前核对每段帧数、最终尺寸/帧数/时长，再完整解码全片音视频。它证明实际文件可解码及排程一致，不能证明审美、风格相似度或人工完整观看通过。当前不伪造人工签字，也不要求用户批准才能生成可审阅成片。

`video-maker/tools/review_film.py OUTPUT_DIR` 直接从实际 MP4 提取逐段、动作结束及片头片尾证据帧，写出与成片 SHA-256 绑定的清单。它与渲染器内的预览帧分开，不把选帧冒充全片审查。

验证：

```powershell
.\mvnw.cmd -pl video-maker -am verify
video-maker/.venv/Scripts/python.exe -m unittest discover -s video-maker/tools/tests -v
```

Java 测试覆盖实际 360 态可达分量、动作合法性与奇偶、14步最短解、12态环和堵塞编码管道的超时清理；Python 测试验证真实词时间、动作绑定失败和 51 段 PCM 拼接无累计漂移。真实全片制作另形成媒体检查收据。

## 参考工程的使用方式

参考 `Z:/workspace/xar_promo_toolchain` 的公开分层：项目意图与执行产物分开、配音提供方隔离、内容寻址缓存、失败材料保留、自动检查与人工观看分开。参考其 TTS/provider、cache、render、audio 模块；本实现使用 Java 主干与数学图形适配器，未引入该项目 Python 包或复制其项目策略、签字/发布流程。没有向那个仓库写入内容。
