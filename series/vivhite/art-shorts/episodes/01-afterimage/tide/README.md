# 白绮／余像·潮汐

《余像》的音乐长版。以 v2 的白绮伸臂插画为主体原画，补绘仰头伸手及低头观水两种姿态。九章用墨蓝、青绿、淡紫和银白的变化呈现水纹、光轨与 3:2 李萨如图。MP4 为原生 2112×768、30 fps，沿用 2.75:1 的超宽构图。

## 音轨与画面

采用用户指定的本地 `BV1Ce4y1k7pX_p1` M4A。时长取实际音轨时间基，48,000 Hz 下共 86,628,336 个采样单位，即 30 分 04.757 秒。制作器完整解码并提取低频、中频及高频等五组特征，在每个输出帧的真实时刻分别驱动水纹、亮度、粒子和采样光点。分析音频的单声道降采样只用于特征提取，交付使用原立体声 AAC 数据。

音频特征中可见约 22.281 秒的重复乐句。九章各接近九个乐句，实际切点按完整音轨长度取整到最近的画面帧。每章使用独立姿态、景别和配色组合，绘制时继续读取该时刻的音乐特征和持续变化的相位。章节名也可在支持 MP4 章节的播放器中选择。全部切点、姿态及文本为[生产计划](production-plan.json)所列。

| 开始 | 章节 | 人物构图 |
| --- | --- | --- |
| 00:00.000 | 潮纹 | 向右伸手，青绿水纹 |
| 03:20.533 | 浮光 | 向左仰望，蓝白反光 |
| 06:41.067 | 折射 | 向右伸臂近景，蓝紫色 |
| 10:01.600 | 深庭 | 俯看水流，深紫光场 |
| 13:22.133 | 静湾 | 向左仰望，青绿开阔构图 |
| 16:42.633 | 逆流 | 向左伸手近景，冷蓝光场 |
| 20:03.167 | 流银 | 放低手腕，银白反光 |
| 23:23.700 | 微明 | 向右伸手，暖紫光场 |
| 26:44.233 | 回声 | 俯看并渐隐，蓝青收束 |

图中的紫或青色分量对应 `x = sin(3θ + φ)`，暖色分量对应 `y = sin(2θ)`；两轨上的标点与李萨如图中的采样星点共用 `θ`。组合图和人物始终位于同一海报构图中，衣摆位移与水纹由浏览器实时合成。补绘素材位于私有角色库 `characters/vivhite/assets/afterimage/`。[ImageGen 提示词](imagegen-prompts.md)

## 复现

需要 Python 3.12+、NumPy、Node.js、Chrome、FFmpeg、ffprobe、Noto Serif SC、Consolas 和经过哈希绑定的源音乐与三张 PNG。通过[这里的运行时安装步骤](../revision-2/README.md#制作与复现)准备 Playwright 依赖。制作入口会快照所有输入，并在正式编码前检查角色审核收据。

```powershell
$episode = 'series/vivhite/art-shorts/episodes/01-afterimage'
$runtime = '../vivhite-analysis-output/live2d-runtime'
$assets = '../vivhite_characters/characters/vivhite/assets/afterimage'
$audioPath = Read-Host '输入指定 p01 M4A 文件的完整本地路径'
video-maker/.venv/Scripts/python.exe video-maker/tools/produce_music_visualizer.py `
  --episode "$episode/episode.json" `
  --plan "$episode/tide/production-plan.json" `
  --portraits $assets --sound $audioPath --runtime $runtime `
  --chrome 'C:/Program Files/Google/Chrome/Application/chrome.exe' `
  --output '../vivhite-analysis-output/vivhite/art-shorts/01-afterimage/reproduction-tide'
```

构建按章保存 H.264 中间段。封装把画面置于 48 kHz 时间基，正常帧各占 1,600 个时基单位，末帧为 1,136。音频原包复制，两条轨的时长均精确等于源音轨。成片和原音乐存于本地，Git 保存可复现计划和验证记录。

## 验证

实测使用 NumPy 2.5.4、Chromium 158 与 FFmpeg 8.1.1。最终文件中 54,143 帧及全部音频完成解码，逐包核对画面时码和末帧长度，原 AAC 包哈希一致。实际编码画面每章检查六处，共 54 处。人物语义审核覆盖全部九章，人工全片观看范围未记录。[制作结果](production-result.json)
