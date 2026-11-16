# 秋日旅程：片尾修订 v4

本版修改 S48（03:16–03:22，6 秒）的蓝蝶动作和片尾文字。完整影片仍为 202 秒、48 镜、1920×1080／30fps、6,060 帧。v3 成片、导演稿、合成计划与全部历史素材完整保留。

## 画面与文字

蓝蝶以原视频 **1/8 的速度**缓慢开合翅膀，采用八倍时间伸展和运动补偿插帧，输出 144 帧／24fps 的新源片，再统一到 180 帧／30fps。选用原源片开头约 0.75 秒的动作，带有插帧所需的额外输入帧；不通过循环或静止尾帧填满 6 秒。整幅海岸也随之放慢，海浪与镜头运动更轻。末尾 0.8 秒继续淡出。

片尾天空只出现两行，正文分别为：

```text
白绮|秋日旅程
献给最可爱的你
```

不显示英文副题、影像工具、模型、音乐制作方式或其他署名。制作来源只保存在工程记录。S06 的原有片名保持原版本；本次修改范围是用户指定的 S48。

前 47 镜的选用源片字节、顺序、时长与 v3 一致。原先审核的 202 秒纯器乐与合成环境声音轨继续使用，没有对白、旁白、可辨人声或模型原生音频。真人不露脸、不新增原图没有的人员、出场人物全部女性及服装要求继续适用于所有画面。

## 文件与复现

- 完整影片：仓库外 `../vivhite-analysis-output/vivhite/autumn-journey/production-v4-closing-001/film.mp4`。
- 单独片尾：同目录 `closing-preview.mp4`，从实际完整成片精确导出最后 6 秒。
- [最终合成计划 v5](../final-assembly-plan-v5.json)绑定本次实际视频、标题、音轨和修订收据；[交付清单 v4](../delivery-plan-v4.json)记录成片指纹与检查覆盖。
- 全部新增检查图片保存在本期 `assets/generated/production-v4-closing-001/` 并提交 Git。视频、音频和逐帧数值记录保存在仓库外。

准备脚本仅处理本期已交付基线，不调用远程模型，也不自动给出审核通过结论：

```powershell
$episodeRoot = 'series/vivhite/autumn-journey/episodes/01-autumn-journey'
$previous = '<production-v3-realism-002 绝对路径>'
$revision = '<新运行目录，不能是已有成片目录>'
video-maker/.venv/Scripts/python.exe "$episodeRoot/production/prepare-closing-revision.py" --previous $previous --destination $revision
# 新片尾全部入片帧和最终文字实际审阅后，记录选片结论并导出人格／披露绑定收据。
video-maker/.venv/Scripts/python.exe video-maker/tools/reference_finisher.py finish --episode "$episodeRoot/episode.json" --plan "$episodeRoot/final-assembly-plan-v5.json" --directory $revision
```

## 检查范围

本轮助手查看新慢放源片的全部 144 帧、144 个蝶翼局部，以及最终编码片尾的全部 180 帧；原 47 镜复用已有完整审阅，逐镜核对实际 SHA-256 相同，不声称本轮重新看过这些原帧。最终全片另做完整音视频解码、6,060 帧格式／时长核验及逐帧画面对照；音轨与此前已审阅版本进行全量比对。标题逐字检查，片尾只含上述两行。

人格一致性与信息披露分别复审，详细依据只在私有角色库，公开仅保存版本绑定收据。检查方式为助手语义审阅和机器全帧处理；没有人工完整回放或人工审美验收记录。运动补偿插帧仍可能保留细小的蝶翼纹理变形。

验证：制作 worker 15 项 Python 测试、角色绑定 9 项边界测试通过。本次未修改 Java。
