# 《琵琶曲》原片还原版制作交接

本期为「神隐黑炎 vs 虚人梦」。用户授权本期按提供的角色图与指定分工制作。画面以 Kotte Animation 原片为基准，按真实切点拆成 48 镜，每镜用本镜原片和换角构图独立渲染。保留原片的道具、场景、机位、焦点、动作与光效，整片使用「成都超人 p01 原曲」参考版的配乐。目标为 1344×768、24 fps、1478 帧、61.583 秒。 [本期清单](../series/pipa/versus/episodes/01-shenyin-heiyan-vs-xuren-meng/episode.json) · [定稿镜头表](../series/pipa/versus/episodes/01-shenyin-heiyan-vs-xuren-meng/production/shot-plan-v3.json) · [逐镜制作与验收记录](../series/pipa/versus/episodes/01-shenyin-heiyan-vs-xuren-meng/production/source-fidelity-revision.md)

## 交接进度

| 项目 | 交接记录 |
| --- | --- |
| 逐镜验收 | 18／48 镜通过（37.5%），覆盖原片 517／1478 帧。通过镜头为 S01–S12、S14–S17、S20、S22。 |
| 完整成片 | 等待全部镜头通过。 |
| 最新已验收预览 | 原片开头 `[0,463)`，连续 16 镜、19.292 秒。463 个输出画面与通过版的解码哈希一致，15 个切点已对照，指定配乐覆盖每声道 926,000 个采样。 [本机 MP4](D:/workspace/vivhite-analysis-output/pipa/versus/01-shenyin-heiyan-vs-xuren-meng/full-768p-002-source-fidelity/previews/original-0000-0463-1795755438660068600/pipa-768p-preview.mp4) · [验收收据](../series/pipa/versus/episodes/01-shenyin-heiyan-vs-xuren-meng/production/source-fidelity-opening-preview-004.json) |
| 经典段样片 | 原片 00:09.000–00:14.000，S08–S12 连续 5 秒。 [验收收据](../series/pipa/versus/episodes/01-shenyin-heiyan-vs-xuren-meng/production/source-fidelity-classic-preview-001.json) |

北京时间 2026-11-27 13:14 核对统一网关，剩余 30 镜中，S19 第二版在渲染，28 镜排队，S24 第一版已审退、等待返工。S19 此前由本项目队列第 19 位移到首位，接续 S24 执行。本次交接保留了这些在途请求及 Windows 定时任务。 [S24 退回记录](../series/pipa/versus/episodes/01-shenyin-heiyan-vs-xuren-meng/production/source-fidelity-S24-review-001.json)

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
- `$r/shots/Sxx/attempt-NNN/` 汇集 `request.json`、`job.json`、`polls.jsonl`、`sources-raw/`、`sources/`、`cut.mp4`、`comparison/`、`review.json` 和适用的 `postprocess.json`。实际提示词、种子、参照顺序和远端任务号以每次请求收据为准。`$r/anchors/requests.json` 保留构图生成记录。交接台账为 `$r/cut-audit/production-ledger-handoff-20261127.json`，S19 的调序依据见同目录 `S19-attempt-002-priority.json`。

## 接手后的逐镜验收

1. 用队列检查脚本核对每镜的最新任务。运行或等待中的请求保留原任务号。服务端完成后，等定时任务下载并归一化，再查看本镜的逐帧对照。用 `progress.json` 的 `visualReviews` 统计通过镜头。若媒体校验中断，先读 `worker.log` 和任务收据，按原任务号恢复下载。已经完整解码的临时切片可按现有恢复脚本和历史记录复核。 [S21 恢复与返工记录](../series/pipa/versus/episodes/01-shenyin-heiyan-vs-xuren-meng/production/source-fidelity-S21-review-001.json)
2. 优先检查开头连续段的两个缺口。S19 第二版覆盖 `[463,510)`，取同一原镜的三处构图检验贴地近景起势、远处墙面变化及收镜。S21 第二版覆盖 `[536,550)`，重点核对高位背视的身体朝向。两镜通过后，可接上已通过的 S20 和 S22，连续预览到第 578 帧之前。源片 S28、S29 中被遮挡的远处神隐黑炎也在演员检查范围内。 [S19 首版问题与返工](../series/pipa/versus/episodes/01-shenyin-heiyan-vs-xuren-meng/production/source-fidelity-S19-review-001.json) · [S28 远景核对](../series/pipa/versus/episodes/01-shenyin-heiyan-vs-xuren-meng/production/source-fidelity-S28-queue-revision-001.json) · [S29 远景核对](../series/pipa/versus/episodes/01-shenyin-heiyan-vs-xuren-meng/production/source-fidelity-S29-queue-revision-002.json)
3. 检查每页原片与候选并排图，覆盖本镜全部帧。检查两位应出现的角色及服饰、原演员残留、道具轮廓、布景、机位、动作阶段及光效时点。在观察文件写出实际核对范围和可见差异，再登记通过或退回。退回时用同一原镜的运动输入，针对失败处补相应源帧构图。能用同镜的生成帧校正时，保存取帧配方并重新对照全镜。每次尝试保留提示词、参照、种子、结果和判断。
4. 例如，S19 的候选下载完成后，运行下面的命令生成对照。只有核对全 47 帧后才填写观察文件并提交实际决定。返工参数可用 `retry --help` 查看，现有定时任务会读取新尝试并使用后续空位。

```powershell
& $py -X utf8 $maker --directory $r compare --shot S19
& $py -X utf8 $maker --directory $r review --shot S19 --decision accepted --frames 47 `
    --method assistant-frame-review --observations "$r/cut-audit/S19-attempt-002-observations.txt"
& $py -X utf8 $maker --directory $r retry --help
```

S24 返工从原片 `[578,633)` 继续。首版全 55 帧已对照。起镜连贯动作和首处闪光滞后，第 602–605 帧附近躯干仍低伏，最后七帧景别过宽且亮闪减弱。运行目录的 `anchors/` 有三张可供第二版使用的同镜构图，依次为 `S24-source-edit-0578.png`、`S24-source-edit-0600.png`、`S24-source-rear-0615.png`。前两张补足起镜和撑地，第三张给出后方低机位。可用 `retry`、三次 `--anchor` 和 `--replace-all-images`，在提示词中注明三张构图各自的源帧以及末段继续推近、重心位移和闪光节拍。第二版等待接手提交。 [S24 首版实际请求和逐帧观察](../series/pipa/versus/episodes/01-shenyin-heiyan-vs-xuren-meng/production/source-fidelity-S24-review-001.json)

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
