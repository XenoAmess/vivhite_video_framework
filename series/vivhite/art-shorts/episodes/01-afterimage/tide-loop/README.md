# 白绮／余像·原构图循环版

同一个 7.2 秒的白绮伸臂海报贯穿全片。直接沿用[《余像》v2 成片](../revision-2/README.md)的原构图、人物动作、轨迹、图例和文字。画面保持 2816×1024、30 fps，250 次完整循环后接下一周期的前 143 帧，恰好覆盖用户指定的《水月与深蓝之树》官网主界面 P01 音轨。声画时长均为 30 分 04.757 秒。

制作器将 216 帧原片重编码一次，得到可在任意帧停止的 H.264 周期。后续循环均复制相同的视频包，无章节元数据，音乐为完整的原立体声 AAC。末帧在 48 kHz 时间基显示 1,136 个单位，从而和音乐在同一时刻结束。

## 复现

在仓库根目录用 Python 3.12+、FFmpeg 和 ffprobe 运行。画面和音乐的文件指纹见[制作计划](production-plan.json)，输出另存到新目录。

```powershell
$episode = 'series/vivhite/art-shorts/episodes/01-afterimage'
$work = '../vivhite-analysis-output/vivhite/art-shorts/01-afterimage'
$picture = "$work/production-v2/delivery/afterimage.mp4"
$audio = "$work/full-music-v1/delivery/inputs/music.m4a"
py -3.12 video-maker/tools/produce_music_loop.py `
  --episode "$episode/episode.json" `
  --plan "$episode/tide-loop/production-plan.json" `
  --picture $picture --sound $audio `
  --output "$work/single-loop-reproduction"
```

`--sound` 也接受用户最初提供的 M4A 路径。通过人物审核与媒体核对后，产出 `afterimage-single-loop.mp4`。

## 验证

对母循环的 216 帧与 v2 原片逐帧比对，平均 PSNR 为 50.07 dB。全片 54,143 帧和完整音频均成功解码，逐包核对了每一帧的时间戳、视频包的重复关系和音频包指纹。角色语义审核覆盖完整画面周期、音乐和末次截取，人工全片观看范围未记录。[制作结果](production-result.json)
