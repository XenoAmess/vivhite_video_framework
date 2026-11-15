# 第一期：秋日旅程

- [导演案](director.md)：参考手法分析、原创故事、32 镜连续预算表与视听调度。
- [周边图像生成说明](image-briefs.md)：选用角色版本、六类主周边、两类替补、母版提示词与场景任务卡。
- [素材清单](reference-assets.json)：用户 ZIP 中 11 张图的指纹与使用范围。
- [期清单](episode.json)：稳定 ID、角色与导演稿入口。

本次为前期文字交付，时码尚未按成片音频锁定。角色 ZIP 已查看，尚未生成周边图片、人物动作、配乐或视频。原图解压副本留在仓库外，公开工程不保存原 ZIP 或原图。

导演案与图像说明是两个独立审核对象，`reviews/` 各保存一份脚本导出的绑定收据，详细依据只在私有角色库维护。审核方式为 `assistant-semantic-review`，不代表人工看过影片或最终美术验收。

本地保留原压缩包和私有角色库时，可以复查当前文字版本：

```powershell
$episode = 'series/vivhite/autumn-journey/episodes/01-autumn-journey/episode.json'
$referenceZip = '<本地 character.zip 路径>'
video-maker/.venv/Scripts/python.exe scripts/character_review.py check --episode $episode --asset $referenceZip
video-maker/.venv/Scripts/python.exe scripts/character_review.py check --episode $episode --document series/vivhite/autumn-journey/episodes/01-autumn-journey/image-briefs.md --asset $referenceZip
```

此处 `--asset` 绑定的是已查看的参考压缩包，不能用于放行正式渲染。后续实际母版、场景、人物、音频及最终制作计划须重新审阅，并传入本次正式制作采用的全部实际外部素材。
