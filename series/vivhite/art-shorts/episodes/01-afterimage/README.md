# 白绮／余像

**当前版本**为[修订 v2](revision-2/README.md)，采用重新绘制的侧身伸臂造型。下文记录初版 Live2D 成片。

一张可循环播放的动态海报。白绮看向随相位变形的李萨如图形，抬手托起一点星光，再眨眼回望。全片为一个连续镜头，7.2 秒，2816×1024，30 fps。沿用参考片的无声形式，全片的文字与动作见[制作计划](production-plan.json)。

## 参考片分析

三段各 6 秒、180 帧，均为单一连续构图，媒体无音轨。全部 540 帧已解码并计算相邻帧差异。视效按每秒 3 格的顺序画面和细节帧检查。

| 上传顺序 | 全段观察 | 用于《余像》的做法 |
| --- | --- | --- |
| 1 · 2816×1024 | 0–2 秒确立暖色人物、深色撕纸与横向波形；2–4 秒亮点仍锚在人手附近，左侧波形微移；4–6 秒标题、图卡和剪贴轮廓维持原位置。 | 米色纸边衬深墨底。人物、标题和图卡维持海报版式，细线把手势连向图表。 |
| 2 · 1920×1080 | 0–2 秒冷白底与蓝紫光球确立对角线；2–4 秒人物悬浮姿势和前景带状轨迹变化；4–6 秒前后层继续相对运动，版面和标识固定。 | 轨迹拆成身前与身后两层，星点和眼神移动制造视线牵引。 |
| 3 · 2816×1024 | 0–2 秒低饱和淡紫人物置于浅圆与黑纸之间；2–4 秒手边亮点、细轨迹和左侧图卡共同指向中心；4–6 秒无切镜，仍由局部变化维持动感。 | 超宽构图，人物背后设浅色圆盘。主色从 Delta 自带的蓝紫、深墨与金饰延展。 |

将各帧缩至宽 320 像素后与首帧比较，灰度差超过 12 的面积峰值依次为 3.2%、20.8%、8.3%。风格判断来自画面里固定版式与局部动画的组合。三段原片用于分析，成片的图形与角色动作均为本期制作。

## 动作与图形

| 时间 | 可见事件 |
| --- | --- |
| 0–2.0 秒 | 标题已在画面中。白绮看向相位图，扫光沿身前细轨滑向右侧。 |
| 2.0–3.9 秒 | 眨眼后抬手，星光悬在掌上。弧线从掌边接向相位图上同一时刻的采样点。 |
| 3.9–5.57 秒 | 白绮眨眼，收回视线并微笑，光点减弱。头和身的动作同时带动发饰物理。 |
| 5.57–7.2 秒 | 手臂和亮点回到起始附近，供下一轮循环。 |

横坐标与纵坐标分别取 `sin(3θ + φ)` 与 `sin(2θ)`。相位差 `φ` 缓慢变化，图上的亮点和分量图上的两个点始终共用同一个 `θ`。人像由用户给定的 Delta 模型文件、原始纹理与物理设置直接生成，手势、眼神和眨眼用 Cubism 参数驱动。纸纹、图卡和前后两层光轨由[本期画面脚本](artwork.js)合成。

## 复现

从仓库根目录运行。需要 Python 3.12+、Node.js、FFmpeg、ffprobe、支持 WebGL 的 Chrome 和系统字体 Noto Serif SC、Georgia、Consolas。实际使用 Chrome 158.0.8127.37、Node.js 24.14.1 和 FFmpeg 8.1.1。运行时清单锁定 PixiJS 及浏览器驱动依赖，模型由私有 `vivhite_characters` 克隆取得。

```powershell
$runtime = '../vivhite-analysis-output/live2d-runtime'
$output = '../vivhite-analysis-output/vivhite/art-shorts/01-afterimage/reproduction-001'
New-Item -ItemType Directory -Path $runtime -Force | Out-Null
Copy-Item video-maker/tools/live2d-runtime/package.json,video-maker/tools/live2d-runtime/package-lock.json $runtime
npm.cmd ci --prefix $runtime --no-audit --no-fund
Invoke-WebRequest -UseBasicParsing https://cubism.live2d.com/sdk-web/core/05/live2dcubismcore.min.js -OutFile "$runtime/live2dcubismcore.min.js"
py -3.12 video-maker/tools/produce_live2d_short.py `
  --episode series/vivhite/art-shorts/episodes/01-afterimage/episode.json `
  --archive ../vivhite_characters/characters/vivhite/assets/Delta.zip `
  --runtime $runtime `
  --chrome 'C:/Program Files/Google/Chrome/Application/chrome.exe' `
  --output $output
```

制作器将计划、画面脚本和模型归档复制到独立运行目录，检查实际用到的字节与审核收据是否匹配，再载入模型。Cubism Core 5.2 的来源为[官方 Web SDK 页面](https://www.live2d.com/en/sdk/download/web/)，制作器校验其 SHA-256。通过校验后离线渲染画面，编码得到 `afterimage.mp4`。失败时保留运行目录中的输入和中间帧。更换脚本或人物素材时按[人物规约](../../../../../docs/character-workflow.md)复审。

## 验证

最终 MP4 的 216 帧均通过完整解码与逐帧时码检查。人物动作用全 216 帧局部画面复查，整幅构图每秒取 6 格并检查关键时刻的原尺寸画面。首尾帧的灰度差低于普通相邻帧差的中位数。人格一致性与信息披露均通过助手语义审核，人工验收待进行。重复渲染所得画面存在微小像素差异，媒体指纹对应本次交付的文件。 [制作结果](production-result.json)
