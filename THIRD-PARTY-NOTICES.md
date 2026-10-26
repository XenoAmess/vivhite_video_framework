# 第三方组件与模型

项目自身采用 GPL-3.0-only。源视频、模型权重和第三方依赖保留各自授权，项目许可证不替代这些授权。源视频、原片截图、模型权重、Python 虚拟环境均不纳入仓库。

| 组件 | 本次版本/用途 | 上游与许可证 |
| --- | --- | --- |
| Jackson Databind / Core / Annotations | Java JSON 契约；Databind/Core 2.20.1，Annotations 由依赖解析 | [FasterXML](https://github.com/FasterXML/jackson-databind)，Apache-2.0；fat jar 保留上游 LICENSE/NOTICE |
| JUnit Jupiter | 5.13.4，仅测试 | [JUnit](https://github.com/junit-team/junit5)，EPL-2.0 |
| Maven Wrapper / Shade | 构建、打包 | [Apache Maven](https://maven.apache.org/)，Apache-2.0 |
| FFmpeg / ffprobe | 外部可执行文件；本机 8.1.1 | [FFmpeg](https://ffmpeg.org/legal.html)，授权依构建选项变化，本仓库不分发二进制 |
| edge-tts | 7.3.1，联网生成晓晓配音与词边界 | [rany2/edge-tts](https://github.com/rany2/edge-tts)，LGPL-3.0；与本项目 GPL-3.0-only 兼容，Python worker 中使用，非 Java 打包依赖 |
| Microsoft YaHei UI | 本机 Java2D 中文字形渲染 | Windows 提供的字体；不把字体二进制纳入仓库，不转授字体许可证 |
| PyAV | 19.0.2，连续解码与 PTS | [PyAV](https://github.com/PyAV-Org/PyAV)，BSD-3-Clause；所链接 FFmpeg 依具体发行包 |
| faster-whisper / CTranslate2 | 1.2.1 / 4.8.3，完整音轨 ASR | [SYSTRAN](https://github.com/SYSTRAN/faster-whisper)，MIT；[CTranslate2](https://github.com/OpenNMT/CTranslate2)，MIT |
| Whisper large-v3-turbo | CTranslate2 转换权重，按需下载到用户缓存 | [原始模型](https://huggingface.co/openai/whisper-large-v3-turbo)、[本次转换模型](https://huggingface.co/mobiuslabsgmbh/faster-whisper-large-v3-turbo)，模型卡标注 MIT |
| RapidOCR / ONNX Runtime | 3.10.0 / 1.31.0，字幕 ROI OCR | [RapidOCR](https://github.com/RapidAI/RapidOCR)，Apache-2.0；[ONNX Runtime](https://github.com/microsoft/onnxruntime)，MIT |
| RapidOCR 内置 OCR 权重 | 本次包内 PP-OCRv6 det/rec 与 ch_ppocr_mobile_v2.0 cls 的 ONNX 模型 | 来自 RapidOCR 包及其 PaddleOCR 模型来源；随包元数据/模型授权保留，不重新分发 |
| OpenCV / NumPy / Pillow | 5.0.0.93 / 2.5.4 / 13.0.0，逐帧差异、数组与联系表 | [OpenCV](https://github.com/opencv/opencv)，Apache-2.0；[NumPy](https://github.com/numpy/numpy)，BSD-3-Clause；[Pillow](https://github.com/python-pillow/Pillow)，MIT-CMU |

Python 完整实跑版本见 `video-analyzer/tools/requirements-lock.txt`；其中传递依赖的许可证以各安装包元数据为准。运行中模型会由上游缓存下载，本次未把模型文件写入 Git。默认模型别名不保证未来上游修订不变；要求位级复现时，应将 `asrModel` 改为固定的本地模型快照路径并保留其指纹。

本例内容参考：白绮Infinity，BV1AV411V7SJ；表达方法参考：真理院七叶，BV1i4aS6SEBR。仓库保存原创改编稿及分析注释，不分发参考片的图像、音轨或完整原片字幕。新稿的配色、版式和声音安排是制作建议，不是对参考片素材的再授权。

本次成片重新生成图形、旁白和字幕，不使用原片音轨或音乐。人物图片由用户提供作为临时占位，原文件保留在用户图片目录，不提交到 Git；其素材权利不因工程 GPL 声明而改变。Edge 是微软在线服务，`edge-tts` 的开源许可证不替代服务条款。配音环境完整版本见 `video-maker/tools/requirements-lock.txt`。
