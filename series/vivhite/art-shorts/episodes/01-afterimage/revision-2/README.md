# 《白绮／余像》修订 v2

7.2 秒、2816×1024、30 fps 的无声循环短片。白绮侧身，双臂沿相反的斜线展开。画面右侧的手伸入图框，视线随倾斜的头部指向伸展的一侧。发带和衣摆向反方向流动，采样星点在手臂抬展到最高处时靠近指尖。初版的参考片分析和制作记录仍在[原期目录](../README.md)。

## 人物与图形

- 以 Delta 模型渲染图和头像为外观参考，用内置 ImageGen 重画透明插画。原画延续银蓝短发、金边圆眼镜、黑金外套和蓝色衣带。选用的原始 PNG 保存在私有角色库的 `characters/vivhite/assets/afterimage/afterimage-v2-reaching.png`。[生成提示词](imagegen-prompt.md)
- 将原画映射到网格上，对肩、手腕、头发、衣带与衣摆进行局部变形。抬手、转腕和衣料位移由同一周期控制，指尖位置从网格变换计算。星光靠近时，暖色亮度只作用于人物图层的手部附近。
- 左图紫线对应 `x = sin(3θ + φ)`，金线对应 `y = sin(2θ)`。两处标记使用相同的 `θ`，右图星点横纵坐标来自左图的两个值。右图注明 `φ` 为相位差。星点在指尖附近减速，两张图继续共用同一采样参数。

## 制作与复现

准备同级私有角色库，安装 Node.js、Chrome、Python 3.12+、FFmpeg、ffprobe 和 Noto Serif SC、Georgia、Consolas 字体。浏览器网格动画的依赖版本已锁定，若已安装则直接运行制作器。

```powershell
$episode = 'series/vivhite/art-shorts/episodes/01-afterimage'
$runtime = '../vivhite-analysis-output/live2d-runtime'
$output = '../vivhite-analysis-output/vivhite/art-shorts/01-afterimage/reproduction-v2'
New-Item -ItemType Directory -Path $runtime -Force | Out-Null
Copy-Item video-maker/tools/live2d-runtime/package.json,video-maker/tools/live2d-runtime/package-lock.json $runtime
npm.cmd ci --prefix $runtime --no-audit --no-fund
py -3.12 video-maker/tools/produce_live2d_short.py `
  --episode "$episode/episode.json" `
  --plan "$episode/revision-2/production-plan.json" `
  --portrait '../vivhite_characters/characters/vivhite/assets/afterimage/afterimage-v2-reaching.png' `
  --runtime $runtime `
  --chrome 'C:/Program Files/Google/Chrome/Application/chrome.exe' `
  --output $output
```

生成 `afterimage.mp4` 前，制作器检查实际输入的图像、画面脚本与[生产计划](production-plan.json)是否匹配人物审核收据。画面字稿和逐段动作也在生产计划内。

## 验证

216 帧全部通过解码和时码检查。助手用 216 格整幅构图以及 10 fps 手部近景复查伸臂、衣带、星光接近和首尾衔接，核对了第 108 帧的原尺寸画面。人物一致性与信息披露分别通过助手语义审核，人工验收待进行。[制作结果](production-result.json)
