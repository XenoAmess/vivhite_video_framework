# 《琵琶曲》原片还原版制作交接

本期为「神隐黑炎 vs 虚人梦」。用户授权本期按提供的角色图与指定分工制作。画面以 Kotte Animation 原片为基准，按真实切点拆成 48 镜，每镜用本镜原片和换角构图独立渲染。保留原片的道具、场景、机位、焦点、动作与光效，整片使用「成都超人 p01 原曲」参考版的配乐。目标为 1344×768、24 fps、1478 帧、61.583 秒。 [本期清单](../series/pipa/versus/episodes/01-shenyin-heiyan-vs-xuren-meng/episode.json) · [定稿镜头表](../series/pipa/versus/episodes/01-shenyin-heiyan-vs-xuren-meng/production/shot-plan-v3.json) · [逐镜制作与验收记录](../series/pipa/versus/episodes/01-shenyin-heiyan-vs-xuren-meng/production/source-fidelity-revision.md)

## 交接进度

| 项目 | 交接记录 |
| --- | --- |
| 逐镜验收 | 48／48 镜通过，连续覆盖原片 `[0,1478)`。最后通过 S28。 |
| 完整成片 | 11 月 28 日 10:24 合成，1344×768、24 fps、1478 帧、61.583 秒。已完整解码，核对全部 1478 帧、47 个切点及每声道 2,956,000 个配乐采样。 [本机 MP4](D:/workspace/vivhite-analysis-output/pipa/versus/01-shenyin-heiyan-vs-xuren-meng/full-768p-002-source-fidelity/pipa-768p.mp4) · [成片验收收据](../series/pipa/versus/episodes/01-shenyin-heiyan-vs-xuren-meng/production/source-fidelity-final-768p.json) |
| 全部通过镜头样片 | 11 月 28 日 10:04 合成，按原片顺序拼接 47 镜、1439 帧，共 59.958 秒。画面与配乐同步跳过 S28 的 `[671,710)`。样片已完整解码，核对 46 个切点与每声道 2,878,000 个配乐采样。 [本机 MP4](D:/workspace/vivhite-analysis-output/pipa/versus/01-shenyin-heiyan-vs-xuren-meng/full-768p-002-source-fidelity/previews/approved-47-1439-1795831474399133900/pipa-768p-approved-preview.mp4) · [验收收据](../series/pipa/versus/episodes/01-shenyin-heiyan-vs-xuren-meng/production/source-fidelity-approved-preview-47.json) · [上版 44 镜收据](../series/pipa/versus/episodes/01-shenyin-heiyan-vs-xuren-meng/production/source-fidelity-approved-preview-44.json) |
| 经典段样片 | 原片 00:09.000–00:14.000，S08–S12 连续 5 秒。 [验收收据](../series/pipa/versus/episodes/01-shenyin-heiyan-vs-xuren-meng/production/source-fidelity-classic-preview-001.json) |
| S20–S22 样片 | 原片 `[510,578)`，连续 3 镜、2.833 秒。68 帧与通过版的解码哈希一致，已对照 2 个切点和每声道 136,000 个配乐采样。 [本机 MP4](D:/workspace/vivhite-analysis-output/pipa/versus/01-shenyin-heiyan-vs-xuren-meng/full-768p-002-source-fidelity/previews/original-0510-0578-1795792365501570000/pipa-768p-preview.mp4) · [验收收据](../series/pipa/versus/episodes/01-shenyin-heiyan-vs-xuren-meng/production/source-fidelity-S20-S22-preview-001.json) |

北京时间 2026-11-28 10:22 下载 S28 第五版。成片取同镜第二版的快速拉远和粉椅后的神隐黑炎，接上第五版的换脚、双臂前伸与双靴落地。逐帧检查全部 39 帧，核对原尺寸首尾。 [第五版与取帧配方](../series/pipa/versus/episodes/01-shenyin-heiyan-vs-xuren-meng/production/source-fidelity-S28-review-005.json) · [早先逐镜复核与返工](../series/pipa/versus/episodes/01-shenyin-heiyan-vs-xuren-meng/production/source-fidelity-handoff-review-001.json)

## 文件和生产入口

下列 PowerShell 命令从仓库根目录运行。路径在原制作机上有效。

```powershell
$r = 'D:/workspace/vivhite-analysis-output/pipa/versus/01-shenyin-heiyan-vs-xuren-meng/full-768p-002-source-fidelity'
$previous = 'D:/workspace/vivhite-analysis-output/pipa/versus/01-shenyin-heiyan-vs-xuren-meng/full-768p-001'
$py = 'video-maker/.venv/Scripts/python.exe'
$maker = "$r/runtime/worker-v13/render-shotwise.py"
$task = 'Vivhite-Pipa-Shenyin-Heiyan-Xuren-Meng-768P-002'

Get-ScheduledTask -TaskName $task | Select-Object TaskName, State
Get-Content -Raw -Encoding UTF8 "$r/progress.json"
Get-Content -Encoding UTF8 "$r/worker.log" -Tail 20
& "$r/cut-audit/verify-remaining-queue.ps1" -Run $r
```

- 画面源为 `Z:/workspace/bilibili-download-skill/downloads/BV1pvY16QEwd/` 下的 `琵琶曲丨4K原版 无水印 Kotte Animation素材【全站最高清】 [BV1pvY16QEwd].mkv`。指定分镜和配乐参考为 `Z:/workspace/bilibili-download-skill/downloads/BV14BeA6CEUb/` 下的 `琵琶曲 l 成都超人 p01 原曲 [BV14BeA6CEUb_p1].mkv`。
- `$r/prepared.json` 绑定定稿计划、原片切片、角色构图和配乐的路径及哈希。对齐后的 WAV 位于 `$previous/soundtrack-cut-sync-30f73ed6298c.wav`。旧版任务已退出生产，旧运行目录仍提供当前版使用的音频和源镜素材。
- 角色以入库的两张全身图为准。神隐黑炎穿深蓝金边、长衣摆军服。虚人梦为金发、红兜帽、深色长裤，左肩侧面具随视角遮挡。两人保持接近的身高与头身比。 [角色图与生成记录](../series/pipa/versus/episodes/01-shenyin-heiyan-vs-xuren-meng/assets/generated/character-concepts-v2/)
- Windows 任务使用固定的 `worker-v13`。它约每 60 秒查询统一网关，按任务号下载并核对哈希，按原镜帧数处理切片。768P 模型为 `fasth3-omni-bf16`，服务端同模型最多 32 个未完成任务，GPU 一次运行一个镜头。成功下载的候选留给接手人逐镜审阅。 [统一网关和恢复方式](local-video-768p-4k.md)
- `$r/shots/Sxx/attempt-NNN/` 汇集 `request.json`、`job.json`、`polls.jsonl`、`sources-raw/`、`sources/`、`cut.mp4`、`comparison/`、`review.json` 和适用的 `postprocess.json`。实际提示词、种子、参照顺序和远端任务号以每次请求收据为准。`$r/anchors/requests.json` 保留构图生成记录。最终台账为 `$r/final-production-ledger.json`，包含所有尝试、逐镜验收与成片哈希。

## 逐镜验收方法

1. 用队列检查脚本核对每镜的最新任务。运行或等待中的请求保留原任务号。服务端完成后，等定时任务下载并归一化，再查看本镜的逐帧对照。用 `progress.json` 的 `visualReviews` 统计通过镜头。若媒体校验中断，先读 `worker.log` 和任务收据，按原任务号恢复下载。已经完整解码的临时切片可按现有恢复脚本和历史记录复核。 [S21 恢复与返工记录](../series/pipa/versus/episodes/01-shenyin-heiyan-vs-xuren-meng/production/source-fidelity-S21-review-001.json)
2. S28 的关键检查项为开场粉椅附近被遮挡的神隐黑炎、第 674 帧附近快速拉远、第 682–685 帧短促换脚，以及末段双前臂向前伸出、双脚落地。 [S28 实际请求与构图指纹](../series/pipa/versus/episodes/01-shenyin-heiyan-vs-xuren-meng/production/source-fidelity-handoff-review-001.json)
3. 检查每页原片与候选并排图，覆盖本镜全部帧。检查两位应出现的角色及服饰、原演员残留、道具轮廓、布景、机位、动作阶段及光效时点。在观察文件写出实际核对范围和可见差异，再登记通过或退回。退回时用同一原镜的运动输入，针对失败处补相应源帧构图。能用同镜的生成帧校正时，保存取帧配方并重新对照全镜。每次尝试保留提示词、参照、种子、结果和判断。
4. 用下例复查 S28 的全部 39 帧和已经登记的观察。新候选的登记使用 `review --help`，返工使用 `retry --help`。后续修订使用独立生产目录保存新尝试。

```powershell
& $py -X utf8 $maker --directory $r compare --shot S28
Get-Content -Raw -Encoding UTF8 "$r/shots/S28/attempt-005/review.json"
```

## 全片验收与交付

- [x] 48 个最新镜头各自通过，逐镜记录和合成所用文件哈希绑定一致，覆盖原片 `[0,1478)`。
- [x] 定时任务完成拼接。已核对 `$r/pipa-768p.mp4` 与 `$r/final-receipt.json` 的哈希。
- [x] 完整解码成片。1478 个画面逐帧与通过版的解码哈希一致。已查看 `$r/cut-audit-final/adjacent-cuts-*.jpg` 的全部 47 个切点，核对相邻画面的机位、人物、动作和光效。
- [x] 指定配乐完整解码并在同一采样位置对照。48 kHz 双声道共检查每声道 2,956,000 个采样，最弱一秒相关系数为 0.996722。
- [x] 最终台账、本期制作记录和验收收据均已输出。成片覆盖助手逐镜与切点检查，人工连续播放复核待进行。源素材、候选和成片媒体保留在仓库外。

```powershell
& $py -X utf8 "$r/cut-audit/final-cut-audit.py" $r
& $py -X utf8 "$r/cut-audit/final-soundtrack-audit.py" $r
& $py -X utf8 "$r/cut-audit/export-production-ledger.py" $r --final
```
