# 秋日旅程：对话断开后的独立4K执行

2026-11-18用户要求：即使GPT对话中断，4K视频渲染仍持续正常进行。本期已实际创建并启动带每分钟看护的Windows任务`Vivhite-Autumn-Journey-v11-4K`。这不是仅提供一个待运行的脚本。

## 当前运行与实测证据

独立进程链实际为`svchost.exe → pythonw.exe → durable_video_controller.py → local_video_pipeline.py`，脱离对话终端的进程树。Windows任务处于`Running`，`ExecutionTimeLimit=PT0S`，没有开机或登录触发器；首次按需启动后由每分钟的周期触发器看护。单实例策略为`IgnoreNew`，运行中的任务不会因周期触发而重复启动。完成技术预览或收到明确停止标记时，控制器会尝试禁用看护任务，结果写入`watchdogDisabled`。

实际故障注入只终止了原对话终端下的本地轮询客户端，不取消服务端任务。独立执行器在约15秒内启动新客户端，新客户端的父进程是独立执行器。服务端继续相同任务`video_gen_d9e799b6cbfd4b91a34d71e006dbb267`，创建时间及完整请求指纹保持不变；队列只见这一个原任务，没有重复提交。重复启动同名Windows任务后，控制器与客户端PID均保持原值。

这是客户端突然中断实验及进程归属检查；没有把“实际关闭ChatGPT应用”写成已执行的试验。[可核对收据](../series/vivhite/autumn-journey/episodes/01-autumn-journey/production/background-continuity-v11-4k.json)保存本次进程链、续接时间上界、任务ID和约束。

另实际终止了独立控制器本身。单靠Windows“失败后重启”配置没有按预期恢复，因此改为每分钟的独立看护触发器；再次终止控制器后，61.535秒内由Windows重新启动并接回同一客户端。服务端原任务在测试期间继续完成，没有取消或重提。保留失败对照与成功记录，不把未生效的配置当作保证。

## 自动推进的环节

控制器始终沿用[已审4K计划](../series/vivhite/autumn-journey/episodes/01-autumn-journey/production-plan-v11-native-4k.json)，冻结实际运行代码和输入指纹。客户端或短暂网络错误导致进程退出时，先确认旧客户端是否仍存活，再续接已保存的任务；未知POST受理状态不会盲目重提。模型终止失败、素材绑定改变及检查失败记录为需检查，不能通过伪造结果继续。

在不需要GPT参与的情况下，程序依次完成：

1. 按用户最新要求，以客户端窗口4预排原生3840×2160任务，保持1个运行＋3个等待；HTTP每60秒查询已知任务ID，GPU仍单窗口推理。
2. 下载原始视频及音轨，核对服务端哈希，保存规范化24fps源片、完整请求、日志、轮询及失败材料。
3. 解码全部完整源帧，导出动作、场景变化和人脸候选检查图片；这些机器候选不代表内容通过。
4. 将完整源片的检查图片与不含私有人格的生成清单按路径提交、推送Git。有其他已暂存文件时延后检查点，避免混入其他工作；Git失败不终止视频生成。
5. 48镜齐备后自动合成完整**未审4K技术预览**：3840×2160、30fps、205秒／6150帧，使用同一音乐、标题及全部镜头时长，并完整解码核对。

完整预览输出在仓库外：

```text
../vivhite-analysis-output/vivhite/autumn-journey/
  production-v11-native-4k-001/
    technical-preview/film-unreviewed.mp4
    technical-preview/receipt.json
```

预览入口明确要求`--technical-preview-only`，不会生成正式`film.mp4`、伪造人格／披露／画面审核、创建通过收据或自动发布正式Release。返回对话后仍应审阅真实4K源帧、手部与印花细节，再按正常正式合成及发布流程交付。技术预览可播放，不等于内容及审美验收已通过。

## 状态、日志和启动位置

本机运行目录为`D:/workspace/vivhite-analysis-output/vivhite/autumn-journey/production-v11-native-4k-001/`。保留：

- `metadata/durable-controller-config.json`：本机路径、固定版本指纹和启动参数，不提交这份本地配置。
- `metadata/scheduled-task.xml`：实际Windows任务定义的导出副本。
- `runtime/controller-007/`：当前控制器、生成客户端、进度导出和技术预览的冻结代码。001至006全部保留，配置核对保留的实际文件。后续仓库改代码不会热改正在运行的任务。
- `controller.json`：控制器及客户端PID、创建时间、心跳、重启次数和当前阶段。
- `logs/durable-controller.log`与`logs/durable-generation-*.log`：独立日志，不依赖对话输出。
- `recovery-test/`：实际中断实验前后记录；`attention.json`出现时应阅读具体失败，不把它视为通过。
- `git-checkpoint.json`：已保存源片检查的提交与推送状态。

[实时进度](../series/vivhite/autumn-journey/episodes/01-autumn-journey/production/run-progress-v11-4k.json)约每20秒更新，区分源片生成、内容审核、技术预览、正式影片和Release。其时间戳会在任务进行时持续改变，不要求GPT保持连接。[源片生成清单](../series/vivhite/autumn-journey/episodes/01-autumn-journey/production/source-generation-v11-4k.json)初始为空，随完整源片及其检查完成而更新。

在本机重新按需启动相同任务，使用：

```powershell
./scripts/start-durable-video-task.ps1 -Configuration `
  D:/workspace/vivhite-analysis-output/vivhite/autumn-journey/production-v11-native-4k-001/metadata/durable-controller-config.json

Get-ScheduledTask -TaskName Vivhite-Autumn-Journey-v11-4K
Get-ScheduledTaskInfo -TaskName Vivhite-Autumn-Journey-v11-4K
```

启动脚本遇到同名无关任务会拒绝覆盖；同一任务已运行时不会再启动第二个执行器。停止本轮时，先在运行目录写入明确的`control/stop.json`，控制器据此停止本地客户端；服务端仍在运行的本项目任务需另行明确取消。不要仅杀轮询进程来表达停止意图，正常恢复策略会重新接管它。

## 保证范围与验证

本轮已验证对话所属客户端突然退出后的自动续接、独立控制器退出后的周期看护恢复与单实例行为；另外七项检查覆盖网络恢复策略、受理不明时禁止重复、源片完整检查后才进入合成、代码版本变化阻止错误续跑、Git不混入其他已暂存文件、提交后崩溃不创建空提交，以及真实原生UHD两秒夹具的合成和全量解码。夹具使用明确的单元测试审核桩，不是实际制作审核。

电脑、当前Windows登录会话及局域网模型服务仍须运行；对话关闭与关机／注销不是同一个条件。执行器只临时防止本机空闲休眠，不修改永久电源计划。服务端OOM暂停、硬件故障和服务重启丢失任务索引属于需单独处理的条件，不承诺这些事件都能无条件自动恢复。实际输入、请求和成品始终保留。

实现入口：[Windows按需任务](../scripts/start-durable-video-task.ps1)、[独立控制器](../video-maker/tools/durable_video_controller.py)、[技术预览合成](../video-maker/tools/render_4k_technical_preview.py)、[当前生成器](../video-maker/tools/local_video_pipeline.py)。正式4K尺寸与质量路线继续遵守[768P／4K规约](local-video-768p-4k.md)，不恢复2K，不改现有768P成片。

## 2026-11-18实际故障与修复

北京时间08:50:30，客户端替换`jobs/S04.json`时发生Windows `WinError 5`，留下完整`.partial`记录后退出。旧控制器只自动恢复网络错误，漏掉了本地JSON替换失败，因而停在`attention-required`。S04仍在服务端继续运行，09:26左右完成；此后GPU队列未被继续推进，直至13:19本次直接检查时恢复。不能把这段空转描述成持续正常渲染。

本次保留旧状态、失败临时文件、控制器配置及原任务，归档于运行目录的`recovery-history/20261118-atomic-json-sharing-failure/`。修复为每个JSON写入使用独立临时文件，对Windows短暂拒绝替换（5／32／33）进行最多10次退避重试；持续失败时保留新旧记录并抛错。控制器仅对明确的JSON临时文件替换错误恢复，仍禁止重复提交受理不明的POST、失败或取消任务。

实际Windows测试用打开的读取句柄阻止文件替换，稍后释放后成功保存；另验证持续拒绝时有界失败、不覆盖其他临时记录，以及本地错误恢复不会绕过受理不明限制。已部署冻结版本004，13:19:47下载同一S04原任务，13:20:41正常提交S05，没有重做S04或改变已提交计划。

后台守护仅作兜底。助手连接期间直接核对真实队列、任务日志、下载文件与质量证据，发现守护缺陷就修复。[本次恢复收据](../series/vivhite/autumn-journey/episodes/01-autumn-journey/production/recovery-v11-4k-20261118.json)及[阶段审计](../series/vivhite/autumn-journey/episodes/01-autumn-journey/production/quality-audit-v11-4k.md)分别记录运行恢复与实际画面结论。

S03原画修复实际复审后，另部署005以支持已审核的修订源片选择。只替换控制器，续接同一004客户端PID `13016`与同一S05服务端任务，生成进程未停止。技术预览对修订文件、原始父文件、修订收据、完整帧检查和实际通过结论逐一绑定；原始问题源片不会被修订文件覆盖。修改选择后不能静默复用旧预览缓存，源片选择在合成中变化则保留中间文件并报错。

14:57另修复控制器自身的完成判定：旧代码只匹配预览文件哈希，可能在素材选择或制作绑定改变后仍把旧预览判为完成并关闭兜底。现在还核对源计划、当前素材选择指纹、音乐、字幕、3840×2160／30fps／6150帧／205秒及完整解码收据。相关7项恢复与完成判定测试通过；这是技术预览有效性检查，不授予内容通过结论。

修复部署为006；只更换经过路径核对的旧守护进程，新守护PID `129376`续接同一客户端PID `13016`及其创建时间，服务端S06任务ID保持不变。归档在`recovery-history/20261118-preview-completion-binding/`。S05完整源片120帧已实际审阅通过，14:38:43提交S06，15:00前后仍在正常计算；所有镜头时长和模型参数均保持已提交计划。

15:36按用户新要求部署007：客户端旧逻辑把4K推理单窗口误当成只能排一个HTTP任务，已解除这一排队限制。新客户端保留S06既有服务端任务，补入S07、S08、S09，实际队列已核对为1个运行＋3个等待，轮询间隔60秒。为应用参数，只重启本机轮询客户端；没有取消或重做服务端推理。守护继续作为兜底，助手主要处理出片审核、修订和异常，不再反复查询或汇报模型块数。
