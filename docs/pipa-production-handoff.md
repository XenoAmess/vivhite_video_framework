# 《琵琶曲》原片还原版制作交接

本期为「神隐黑炎 vs 虚人梦」。用户授权本期按提供的角色图与指定分工制作。画面以 Kotte Animation 原片为基准，按真实切点拆成 48 镜，每镜用本镜原片和换角构图独立渲染。保留原片的道具、场景、机位、焦点、动作与光效，整片使用「成都超人 p01 原曲」参考版的配乐。目标为 1344×768、24 fps、1478 帧、61.583 秒。 [本期清单](../series/pipa/versus/episodes/01-shenyin-heiyan-vs-xuren-meng/episode.json) · [定稿镜头表](../series/pipa/versus/episodes/01-shenyin-heiyan-vs-xuren-meng/production/shot-plan-v3.json) · [逐镜制作与验收记录](../series/pipa/versus/episodes/01-shenyin-heiyan-vs-xuren-meng/production/source-fidelity-revision.md)

## 交接进度

| 项目 | 交接记录 |
| --- | --- |
| 逐镜验收 | 34／48 镜通过（70.83%），覆盖原片 960／1478 帧。本轮新增通过 S19、S27、S32、S35、S40、S41、S43。 |
| 完整成片 | 等待全部镜头通过。 |
| 全部通过镜头样片 | 11 月 28 日 02:29 合成，按原片顺序拼接 34 镜、960 帧，共 40.000 秒。开头 `[0,578)` 已接通至 S22，连续 24.083 秒。此后画面和配乐同步跳过 8 处未完成区间。 [本机 MP4](D:/workspace/vivhite-analysis-output/pipa/versus/01-shenyin-heiyan-vs-xuren-meng/full-768p-002-source-fidelity/previews/approved-34-0960-1795804181946905700/pipa-768p-approved-preview.mp4) · [验收收据](../series/pipa/versus/episodes/01-shenyin-heiyan-vs-xuren-meng/production/source-fidelity-approved-preview-34.json) · [上版 33 镜收据](../series/pipa/versus/episodes/01-shenyin-heiyan-vs-xuren-meng/production/source-fidelity-approved-preview-33.json) |
| 经典段样片 | 原片 00:09.000–00:14.000，S08–S12 连续 5 秒。 [验收收据](../series/pipa/versus/episodes/01-shenyin-heiyan-vs-xuren-meng/production/source-fidelity-classic-preview-001.json) |
| S20–S22 样片 | 原片 `[510,578)`，连续 3 镜、2.833 秒。68 帧与通过版的解码哈希一致，已对照 2 个切点和每声道 136,000 个配乐采样。 [本机 MP4](D:/workspace/vivhite-analysis-output/pipa/versus/01-shenyin-heiyan-vs-xuren-meng/full-768p-002-source-fidelity/previews/original-0510-0578-1795792365501570000/pipa-768p-preview.mp4) · [验收收据](../series/pipa/versus/episodes/01-shenyin-heiyan-vs-xuren-meng/production/source-fidelity-S20-S22-preview-001.json) |

北京时间 2026-11-28 02:29 核对统一网关，剩余 14 镜均已受理，S47 在渲染，13 镜排队。S24 第二版因起身滞后和末段推近缺失退回，第三版使用对应原片末帧的新构图。S30 第二版遭遇显存不足，第三版使用一张起镜构图和原镜运动参考。Windows 定时任务继续下载后续候选。 [队列与 S43 复核](../series/pipa/versus/episodes/01-shenyin-heiyan-vs-xuren-meng/production/source-fidelity-S43-review-002.json) · [夜间逐帧复核和两次返工](../series/pipa/versus/episodes/01-shenyin-heiyan-vs-xuren-meng/production/source-fidelity-overnight-review-001.json)

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
- `$r/shots/Sxx/attempt-NNN/` 汇集 `request.json`、`job.json`、`polls.jsonl`、`sources-raw/`、`sources/`、`cut.mp4`、`comparison/`、`review.json` 和适用的 `postprocess.json`。实际提示词、种子、参照顺序和远端任务号以每次请求收据为准。`$r/anchors/requests.json` 保留构图生成记录。最新台账为 `$r/cut-audit/production-ledger-S43-review-20261128.json`，队列快照为同目录 `queue-after-S43-review-20261128.json`。

## 接手后的逐镜验收

1. 用队列检查脚本核对每镜的最新任务。运行或等待中的请求保留原任务号。服务端完成后，等定时任务下载并归一化，再查看本镜的逐帧对照。用 `progress.json` 的 `visualReviews` 统计通过镜头。若媒体校验中断，先读 `worker.log` 和任务收据，按原任务号恢复下载。已经完整解码的临时切片可按现有恢复脚本和历史记录复核。 [S21 恢复与返工记录](../series/pipa/versus/episodes/01-shenyin-heiyan-vs-xuren-meng/production/source-fidelity-S21-review-001.json)
2. S47 第二版完成后，核对原片 `[1234,1256)` 的俯视推近和第 1238 帧附近开始的皱眉、露齿及咬紧。S28 第三版仍要核对粉椅附近被遮挡的神隐黑炎及第 683 帧附近的换脚。 [S47 首版复核](../series/pipa/versus/episodes/01-shenyin-heiyan-vs-xuren-meng/production/source-fidelity-S47-review-001.json) · [S28 第二版复核](../series/pipa/versus/episodes/01-shenyin-heiyan-vs-xuren-meng/production/source-fidelity-S28-review-002.json)
3. 检查每页原片与候选并排图，覆盖本镜全部帧。检查两位应出现的角色及服饰、原演员残留、道具轮廓、布景、机位、动作阶段及光效时点。在观察文件写出实际核对范围和可见差异，再登记通过或退回。退回时用同一原镜的运动输入，针对失败处补相应源帧构图。能用同镜的生成帧校正时，保存取帧配方并重新对照全镜。每次尝试保留提示词、参照、种子、结果和判断。
4. S47 的候选下载完成后，运行下面的命令生成对照。核对全 22 帧后填写观察文件并登记实际决定。返工参数可用 `retry --help` 查看，现有定时任务会读取新尝试并使用后续空位。

```powershell
& $py -X utf8 $maker --directory $r compare --shot S47
$decision = Read-Host '根据逐帧核对输入 accepted 或 rejected'
& $py -X utf8 $maker --directory $r review --shot S47 --decision $decision --frames 22 `
    --method assistant-frame-review --observations "$r/cut-audit/S47-attempt-002-observations.txt"
& $py -X utf8 $maker --directory $r retry --help
```

S24 第三版沿用原片 `[578,633)`，以第 578、600、632 帧锁定起镜、撑地和末段近景。出片后核对起镜前臂动作与早段闪光、第 602–605 帧的躯干抬升，以及末七帧的重心变化、推近和短闪。S30 第三版核对全镜背身、从第 759 帧极近景拉远再推进和屈膝侧移。 [S24 与 S30 实际请求](../series/pipa/versus/episodes/01-shenyin-heiyan-vs-xuren-meng/production/source-fidelity-overnight-review-001.json)

## 全片验收与交付

- [ ] 48 个最新镜头各自通过，逐镜记录和合成所用文件哈希绑定一致，覆盖原片 `[0,1478)`。
- [ ] 定时任务完成拼接后，核对 `$r/pipa-768p.mp4` 与 `$r/final-receipt.json`。若已满足合成条件且定时任务未生成输出，可在确认没有合成进程时用同一 worker 的 `finish` 命令。
- [ ] 完整解码成片，核对 1478 个画面与逐镜通过版的解码哈希一致。审阅 `$r/cut-audit-final/adjacent-cuts-*.jpg` 中的全部 47 个切点，检查接续的机位、人物、动作和光效。
- [ ] 核对指定配乐的整段同步与完整解码，按 48 kHz 检查每声道 2,956,000 个采样。记录机器验证与实际视觉审阅分别覆盖的范围。
- [ ] 导出最终台账，交付可播放 MP4、本期制作记录与验收收据。源素材、候选和成片媒体保留在仓库外，提交可复核记录。

```powershell
& $py -X utf8 "$r/cut-audit/final-cut-audit.py" $r
& $py -X utf8 "$r/cut-audit/final-soundtrack-audit.py" $r
& $py -X utf8 "$r/cut-audit/export-production-ledger.py" $r --final --output "$r/final-production-ledger.json"
```
