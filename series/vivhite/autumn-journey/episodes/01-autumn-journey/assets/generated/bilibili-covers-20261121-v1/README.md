# bilibili 封面：白绮 / 秋日旅程

本次使用内置 **imagegen** 分别生成横版 16:9 和 4:3 封面，参考白绮玩偶母版及本片 S20 高山湖实帧。两张封面采用独立构图，包含秋日高山湖、岩石、白绮玩偶、旅行包和徽章，沿用现有片名；以自然日光和真实材质控制画面亮度。

| 比例 | 实际尺寸 | 上传用 JPEG | 无损 PNG |
| --- | --- | --- | --- |
| 16:9 | 1664×936 | [cover-16x9.jpg](cover-16x9.jpg) | [cover-16x9.png](cover-16x9.png) |
| 4:3 | 1448×1086 | [cover-4x3.jpg](cover-4x3.jpg) | [cover-4x3.png](cover-4x3.png) |

画面文字为两行中文“白绮 /”“秋日旅程”，下方英文“Vivhite · Autumn Journey”。已逐图查看主体、片名、玩偶睁眼、眼镜、徽章、照明及背景，未见真人或额外人物；用户审美验收待定。

完整提示词保存在 [generation-prompts.json](generation-prompts.json)：16:9 使用其中第一条原文和两张参考图；4:3 最终还加入首张封面作为画面风格及字体参考，其完整实际请求见 [generation-4x3-actual-request.json](generation-4x3-actual-request.json)。提示词中请求的像素尺寸与工具实际输出不同，以上表格列出的是实测交付尺寸。

两次原始生成图分别保存为 [cover-16x9-v1-original.png](cover-16x9-v1-original.png) 和 [cover-4x3-v1-original.png](cover-4x3-v1-original.png)。16:9 原图为 1672×941，使用 FFmpeg 从左右各裁 4 像素、上裁 2 像素、下裁 3 像素，得到严格 16:9 的 1664×936；保留区域的 RGB 像素经逐像素比较完全一致。4:3 原图已为 1448×1086，交付 PNG 是其字节一致的副本。JPEG 由对应 PNG 编码，参数为 `-q:v 2`。

[manifest.json](manifest.json) 保存实际尺寸、文件指纹及导出范围；[references/manifest.json](references/manifest.json) 保存本片 S20 第 2250 帧（75 秒）参考图的来源及影片指纹。所有生成原图、参考帧与交付图均保留并纳入 Git，共 7 张图片。

实际制作记录为 [bilibili-covers-20261121-v1.json](../../../production/bilibili-covers-20261121-v1.json)，人格一致性与信息披露审核的公开版本绑定由项目检查脚本导出。最终核对时修正了记录中片名文本的字符编码并重新审核；原始生成图与实际提示词未变。本任务仅交付封面，既有成片及 Release 保持原样。
