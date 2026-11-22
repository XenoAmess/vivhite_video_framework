# 秋日旅程：对话断开后的独立4K执行

2026-11-22结项更新：完整4K已于前一日发布并完成下载验证，用户现已表示满意并结项，见[结项复盘](autumn-journey-retrospective.md)。下文运行状态、预算与未完成事项保留为历史；本页的启动命令供后续明确任务参考，不表示应重新启动本期渲染。

2026-11-21 05:00进展：原48镜已有45镜下载，S45正在运行；S46、S47、新S05和新S20继续普通排队。用户指出部分修复印花面部过亮，现已重新打开光照融合审核，增加[明度复核与修订](autumn-journey-print-lighting.md)，并在正式装配入口阻止沿用未解决的亮脸。后台生成继续；原片、旧修复和全部调色试样保留。下方18:00—22:00是本次明度问题提出前的条件预算，新增复核会占用后处理余量，待修订收敛后再校正发布窗口。

2026-11-21 00:51重新估算：当前S42运行，S43—S47、新S05及新S20等待，共8个剩余任务。17个已完成5秒源片的运行至下载中位耗时76.16分钟；按这一速度，短片预计约09:00收齐。新10秒S20尚无新后端实测，参照14秒整段S48约8小时9分，先为S20预留6—8小时，源片目标15:00—17:00收齐；再预留3—5小时做最后审阅／必要局部修订、205秒合成、完整检查及Release上传，完整4K预计当日18:00—22:00。当前新部署首个短片尚未完成，速度假设仍待校准；新增远端返工、队列竞争或服务中断会顺延。依据与假设见[最新估算收据](../series/vivhite/autumn-journey/episodes/01-autumn-journey/production/release-estimate-v13-4k-20261121.json)，旧预算记录保留。

2026-11-21更新：海边S48实际完成14秒原生4K整段生成，336帧整景和蝴蝶原生局部均已实际审阅，可作为源片。服务器返回 `full_sequence/windows=1` 且不回退到独立视频窗口；首次观察运行到本地下载约8小时9分。下文按四窗估算的旧交付窗口08:00—11:00属于历史预算，现已顺延；新增S20整段重做也需要额外排队与生成，不能继续沿用该旧时间承诺。短镜头预算待新部署的实际出片耗时校准。

用户在该片尾通过后要求再做10秒高山湖／包／玩偶：实际任务 `video_gen_9ff805618a994ab5a4d2b2234cc384de` 已以同一完整768P源片、3840×2160、`up3`、种子1234进入普通队尾，提交后快照为第7位，排在S43—S47和新版S05之后。独立Windows任务 `Vivhite-Autumn-Journey-v13-S20-4K` 已运行，冻结代码、计划、任务ID和完整请求另存于 `production-v13-S20-full-sequence-native-4k-001`；60秒轮询，聊天中断后继续生成、下载、完整机器检查和图片Git检查点，不自动通过画面。原两组生成任务不变，见[排队及守护凭据](../series/vivhite/autumn-journey/episodes/01-autumn-journey/production/S20-full-sequence-submission-v13.json)。

新完整影片改用[独立v13来源导入器](../series/vivhite/autumn-journey/episodes/01-autumn-journey/production/materialize-native4k-sources-v13.py)：46镜原生4K原来源，加单独重做的S05和本次S20。新版S20必须实际通过完整240帧审阅，并核对同一任务的 `full_sequence/windows=1/independent_window_fallback=false`，不能用旧多窗S20回填。原v12导入器、旧计划和缓存全部保留；当前[预检查](../series/vivhite/autumn-journey/episodes/01-autumn-journey/production/native4k-v13-import-preflight.json)在缺少新源片时拒绝、未创建最终合成目录。3项回归检查保护48镜原时序、禁止旧S20回退、禁止缩短S46；正式48素材／计划审核及成片检查仍待完成。

已采用S48另存[第五批合成缓存](../series/vivhite/autumn-journey/episodes/01-autumn-journey/production/reviewed-native4k-segment-cache-v12-005.json)，保持原生4K，转换为14秒／420帧30fps；全部420帧机器对照最低YUV PSNR43.86dB。该缓存与原336帧24fps源片分别保留。最终只导入与实际采用源片哈希、镜长、编码配方及成品指纹全部匹配的缓存；第一批中的旧S20缓存不用于新版S20。不把缓存完成或数值对照当作完整成片语义审核。

2026-11-18用户要求：即使GPT对话中断，4K视频渲染仍持续正常进行。本期已实际创建并启动带每分钟看护的Windows任务`Vivhite-Autumn-Journey-v11-4K`。这不是仅提供一个待运行的脚本。

## 当前运行与实测证据

首次部署的独立进程链实际为`svchost.exe → pythonw.exe → durable_video_controller.py → local_video_pipeline.py`，脱离对话终端的进程树。Windows任务处于`Running`，`ExecutionTimeLimit=PT0S`，没有开机或登录触发器；首次按需启动后由每分钟的周期触发器看护。单实例策略为`IgnoreNew`，运行中的任务不会因周期触发而重复启动。2026-11-20已切换至下面所述的009配置：原批次只收齐源片、检查图片并推送检查点，随后禁用自身看护；正式影片另用通过审核的素材装配。

实际故障注入只终止了原对话终端下的本地轮询客户端，不取消服务端任务。独立执行器在约15秒内启动新客户端，新客户端的父进程是独立执行器。服务端继续相同任务`video_gen_d9e799b6cbfd4b91a34d71e006dbb267`，创建时间及完整请求指纹保持不变；队列只见这一个原任务，没有重复提交。重复启动同名Windows任务后，控制器与客户端PID均保持原值。

这是客户端突然中断实验及进程归属检查；没有把“实际关闭ChatGPT应用”写成已执行的试验。[可核对收据](../series/vivhite/autumn-journey/episodes/01-autumn-journey/production/background-continuity-v11-4k.json)保存本次进程链、续接时间上界、任务ID和约束。

另实际终止了独立控制器本身。单靠Windows“失败后重启”配置没有按预期恢复，因此改为每分钟的独立看护触发器；再次终止控制器后，61.535秒内由Windows重新启动并接回同一客户端。服务端原任务在测试期间继续完成，没有取消或重提。保留失败对照与成功记录，不把未生效的配置当作保证。

## 自动推进的环节

控制器始终沿用[已审4K计划](../series/vivhite/autumn-journey/episodes/01-autumn-journey/production-plan-v11-native-4k.json)，冻结实际运行代码和输入指纹。客户端或短暂网络错误导致进程退出时，先确认旧客户端是否仍存活，再续接已保存的任务；未知POST受理状态不会盲目重提。模型终止失败、素材绑定改变及检查失败记录为需检查，不能通过伪造结果继续。

在不需要GPT参与的情况下，程序依次完成：

1. 按用户最新要求尽量预排全部原生3840×2160任务；同模型服务端上限32个未完成任务，因此客户端窗口32，其余随空位补入。批量模式每60秒读一次队列，仅对运行或已离队任务获取完整状态，GPU仍单窗口推理。
2. 下载原始视频及音轨，核对服务端哈希，保存规范化24fps源片、完整请求、日志、轮询及失败材料。
3. 解码全部完整源帧，导出动作、场景变化和人脸候选检查图片；这些机器候选不代表内容通过。
4. 将完整源片的检查图片与不含私有人格的生成清单按路径提交、推送Git。有其他已暂存文件时延后检查点，避免混入其他工作；Git失败不终止视频生成。
5. 009配置中，48镜齐备并核对完整源帧及已推送检查点后，停在`complete-sources-awaiting-semantic-review`。不自动合成包含旧S05的技术预览，也不授予内容通过。新版完整影片由下述v12素材导入与正式装配流程制作。

旧配置的完整未审预览预定输出在仓库外；009不会自动创建它：

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
- `runtime/controller-009/`：当前只收齐源片的控制器与进度导出冻结代码。实际生成客户端仍运行008，命令和进程未更换；001至008全部保留。后续仓库改代码不会热改正在运行的任务。
- `controller.json`：控制器及客户端PID、创建时间、心跳、重启次数和当前阶段。
- `logs/durable-controller.log`与`logs/durable-generation-*.log`：独立日志，不依赖对话输出。
- `recovery-test/`：实际中断实验前后记录；`attention.json`出现时应阅读具体失败，不把它视为通过。
- `git-checkpoint.json`：已保存源片检查的提交与推送状态。

[实时进度](../series/vivhite/autumn-journey/episodes/01-autumn-journey/production/run-progress-v11-4k.json)约每20秒更新，区分源片生成、内容审核、技术预览、正式影片和Release。其时间戳会在任务进行时持续改变，不要求GPT保持连接。[源片生成清单](../series/vivhite/autumn-journey/episodes/01-autumn-journey/production/source-generation-v11-4k.json)初始为空，随完整源片及其检查完成而更新。

在本机重新按需启动相同任务，使用：

```powershell
./scripts/start-durable-video-task.ps1 -Configuration `
  D:/workspace/vivhite-analysis-output/vivhite/autumn-journey/production-v11-native-4k-001/metadata/durable-controller-config.json

Get-ScheduledTask -TaskName Vivhite-Autumn-Journey-v11-4K-sources
Get-ScheduledTaskInfo -TaskName Vivhite-Autumn-Journey-v11-4K-sources
```

启动脚本遇到同名无关任务会拒绝覆盖；同一任务已运行时不会再启动第二个执行器。停止本轮时，先在运行目录写入明确的`control/stop.json`，控制器据此停止本地客户端；服务端仍在运行的本项目任务需另行明确取消。不要仅杀轮询进程来表达停止意图，正常恢复策略会重新接管它。

## 保证范围与验证

本轮已验证对话所属客户端突然退出后的自动续接、独立控制器退出后的周期看护恢复与单实例行为；另外七项检查覆盖网络恢复策略、受理不明时禁止重复、源片完整检查后才进入合成、代码版本变化阻止错误续跑、Git不混入其他已暂存文件、提交后崩溃不创建空提交，以及真实原生UHD两秒夹具的合成和全量解码。夹具使用明确的单元测试审核桩，不是实际制作审核。

电脑、当前Windows登录会话及局域网模型服务仍须运行；对话关闭与关机／注销不是同一个条件。执行器只临时防止本机空闲休眠，不修改永久电源计划。服务端OOM暂停、硬件故障和服务重启丢失任务索引属于需单独处理的条件，不承诺这些事件都能无条件自动恢复。实际输入、请求和成品始终保留。

实现入口：[Windows按需任务](../scripts/start-durable-video-task.ps1)、[独立控制器](../video-maker/tools/durable_video_controller.py)、[技术预览合成](../video-maker/tools/render_4k_technical_preview.py)、[当前生成器](../video-maker/tools/local_video_pipeline.py)。正式4K尺寸与质量路线继续遵守[768P／4K规约](local-video-768p-4k.md)，不恢复2K，不改现有768P成片。

## 单镜返工的独立看护

2026-11-19用户指出骑行缺车座，先完成并发布v12原始768P修订，再提交对应原生4K。S05使用独立计划、运行目录和Windows任务`Vivhite-Autumn-Journey-v12-S05-4K`，接管同一个已提交客户端，不重提原48镜任务。原控制器008和原计划字节保持。实际部署、任务ID、源片哈希与冻结代码见[S05凭据](../series/vivhite/autumn-journey/episodes/01-autumn-journey/production/S05-native4k-submission-v12.json)。

控制器现在支持显式`generationOnly: true`：只完成指定源片的生成、下载、完整机器检查与图片入库，不创建完整影片预览，也不自动通过画面内容。必须核对实际本地视频哈希、24fps、全部源帧及图片报告覆盖；相同源片／报告的Git检查点已成功推送后才关闭兜底任务，提交被无关暂存文件阻挡时继续等待。

单镜计划不能用镜号数字作数组下标，S05只有一个元素时该做法会越界；现在按稳定镜号查找，并拒绝计划中不存在的任务。`evidenceRelativeToEpisode`和`sourceCatalogRelativeToEpisode`指定该返工自己的检查图与生成台账，路径限制在当期的`assets/generated`与`production`，不会覆盖原48镜台账。未指定这些字段的旧全片配置保持原路径，现有冻结版本不受源码更新影响。测试覆盖单镜ID、独立台账、路径越界、缺失／变更源片、不完整帧报告、过期／未推送Git检查点，以及既有网络恢复、受理不明保护和无关暂存文件保留，共11项通过。

对应完整4K的素材导入另由[`materialize-native4k-sources-v12.py`](../series/vivhite/autumn-journey/episodes/01-autumn-journey/production/materialize-native4k-sources-v12.py)负责：48镜逐一指定来源，S05只认独立返工，其余47镜沿用原生成任务及实际审核选择。它先核对**整批**通过决定、全部源帧证据、原生尺寸、完整解码报告、真实请求／输入／下载哈希和修订收据，再调用已有导入器复制到新装配目录。不提交HTTP任务，不修改旧计划或旧视频，不补写内容通过。

新装配计划须保持每镜原定位置与时长、205秒／6150帧、标题和献词，S05仅将独立返工的镜头位置放回420帧，其余47镜对象不能改变。`build_plan()`只构造待审候选，正式装配仍需全部实际素材及本期角色／披露审核；不能把这个候选当作新的48镜生成任务提交。重新检查实际冻结的008预览代码后发现：修订素材分支有绑定检查，但原始素材分支不会因为拒收决定而停止，不能依赖它拦住旧S05。009因此明确关闭原批次自动预览；v12导入器另要求48份实际采用决定，且S05仅认独立返工目录。

2026-11-20凌晨新增的[5项导入测试](../series/vivhite/autumn-journey/episodes/01-autumn-journey/production/test_materialize_native4k_v12.py)已通过。对当前真实未齐素材的调用也因新版S05尚无采用决定而在创建新装配目录前拒绝，未回填旧版，见[实测收据](../series/vivhite/autumn-journey/episodes/01-autumn-journey/production/native4k-v12-assembly-preflight.json)。这不代表48份4K素材已经齐备或最终装配验收通过。骑行专用全帧机械检查见[后处理文档](autumn-journey-video-postprocessing.md#骑行机械结构的返工与检查)。

新版S05另有[出片后机械检查材料准备程序](../series/vivhite/autumn-journey/episodes/01-autumn-journey/production/S05-native-evidence-preparer-v12.py)，[启动凭据](../series/vivhite/autumn-journey/episodes/01-autumn-journey/production/S05-native-evidence-preparation-wait-v12.json)保留实际代码和配置指纹。它是隐藏窗口启动的独立本地进程，每60秒只读本地文件，不调用模型或修改队列；等指定返工任务、完整下载和120帧报告齐备后，展开车座／臀部、双腿／曲柄及贴纸各120帧原生裁切和全部检测候选。最长等待48小时，失败保留全部材料；代码或绑定改变即停止检查并记录错误，不重提生成任务。程序只准备证据，实际画面阅读、采用决定和Git归档仍由助手执行。固定裁切若随运动截断人物或机械结构，须另存扩大区域，不能将导出成功当作审阅通过。

### 009：原批次停止自动采用旧骑行镜头

2026-11-20北京时间06:29部署009：保留008和全部旧配置，只替换本地守护，采用已有的`generationOnly: true`策略。实际生成客户端PID `201936`及创建时间不变，48份任务ID、请求指纹、提交计划、排队窗口32与60秒轮询均未改变。独立新版S05任务及其守护也保持原样。没有停止或重新提交任何模型任务。

新的Windows任务为`Vivhite-Autumn-Journey-v11-4K-sources`，沿用每分钟看护、`IgnoreNew`及不限时运行。旧同名历史任务仅禁用后续触发并保留定义；没有停止生成客户端的进程树。新控制器已实际接管原客户端，完整源片的解码、图片保存及Git检查点继续执行。配置、旧心跳、旧任务定义与全部任务绑定归档在运行目录`recovery-history/20261120-source-only-controller-009/`。

[部署实测收据](../series/vivhite/autumn-journey/episodes/01-autumn-journey/production/source-only-controller-009-v11-4k.json)记录新旧配置指纹与接管检查。本次实际运行现有控制器恢复测试10项通过；没有为此中断渲染或重做故障注入，也没有把检查图片已导出等同于画面已审通过。

## 2026-11-20发布时间估算与已审核镜头缓存

按S25—S38共14份完整本地记录，从首次运行到下载完成的单窗口镜头中位耗时约76.17分钟。估算时S39运行，余下S40—S47、14秒S48及另排的新版S05计入预算；S48暂按4个窗口估算，尚不是该任务的实测结果。预计北京时间11月21日05:30前后收齐源片，再预留3—5小时完成最后几镜检查、205秒合成、完整检查及Release上传，向用户给出的发布窗口为11月21日08:00—11:00。这个窗口以服务、队列顺序和近期速度持续正常且没有新增远程返工为前提。计算数据和假设保存于[估算收据](../series/vivhite/autumn-journey/episodes/01-autumn-journey/production/release-estimate-v12-4k-20261120.json)，不是交付验收或保证时间。

等待远端生成期间，用[已审核镜头缓存工具](../series/vivhite/autumn-journey/episodes/01-autumn-journey/production/prepare-reviewed-native4k-segments-v12.py)在独立的`production-v12-native-4k-segment-cache-001`准备S01—S38中已采用的37镜，明确排除旧S05。工具在创建目录前核对整批实际采用结论、源片／父片、任务、完整解码报告和所有整景证据指纹；没有修订选择的原片同样必须有明确的`accepted`结论，不能借用旧预览工具的原片回退路径。运行不增加HTTP请求，不提交任务、不合成影片，也不写新的语义通过结论。

每段保留原生3840×2160，按原定入片秒数转换为30fps，采用现有合成器的`fps30-x264-fast-crf17-1`配方；源片仍单独保留完整24fps版本。输出先写`.partial.mp4`，完整读取核对尺寸、帧率和帧数后才生成带实际源片指纹的缓存收据。异常保留部分文件与编码日志。实际旧S05被拒绝且没有创建输出目录、其余37镜的源片与整景证据验证通过；另有[3项回归检查](../series/vivhite/autumn-journey/episodes/01-autumn-journey/production/test_prepare_reviewed_native4k_segments_v12.py)覆盖被撤回原片禁止回退、报告错绑及编码失败保留材料。

已实际完成37段缓存，共151秒／4530个30fps帧，逐文件及收据指纹复核通过。另把全部4530个原生尺寸缓存帧与相同源片的既定30fps转换逐帧机器对照，最低YUV PSNR为42.49dB；每帧统计、解码日志、实际比较程序与输入均保留。这用于检查编码与源帧对应关系，不是逐像素相同、助手逐张语义阅读或成片验收。完整绑定见[缓存实测收据](../series/vivhite/autumn-journey/episodes/01-autumn-journey/production/reviewed-native4k-segment-cache-v12-001.json)。

S39完成实际源片审阅后，另存`production-v12-native-4k-segment-cache-002`，保持第一批缓存原样。新增该镜原定3秒／90帧，全部90个原生缓存帧机器对照最低YUV PSNR为44.23dB，输出和收据指纹复核通过，见[第二批收据](../series/vivhite/autumn-journey/episodes/01-autumn-journey/production/reviewed-native4k-segment-cache-v12-002.json)。两批共38镜／154秒／4620帧，各段独立保存；只有全部48镜正式导入通过后，才按相同源片哈希、帧数、编码配方及输出指纹合入最终缓存目录，并由合成器再次检查。当前没有绕过缺失的新S05拼成完整影片。

S40修订版完成全部120个源帧的实际复审后，单独保存第三批`production-v12-native-4k-segment-cache-003`，未改前两批。新增原定5秒／150个30fps帧，全部原生尺寸帧的机器对照最低YUV PSNR为48.79dB，实际视频、收据、比较统计及程序均保留，见[第三批收据](../series/vivhite/autumn-journey/episodes/01-autumn-journey/production/reviewed-native4k-segment-cache-v12-003.json)。三批累计39镜／159秒／4770帧；仍是分段技术缓存，未合成完整影片，也未授予编码缓存新的语义或成片通过结论。

S41双周边修订版完成实际复审后，另存第四批`production-v12-native-4k-segment-cache-004`，保持其原定4秒／120个30fps帧；全部120个原生尺寸帧机器对照最低YUV PSNR为46.21dB，见[第四批收据](../series/vivhite/autumn-journey/episodes/01-autumn-journey/production/reviewed-native4k-segment-cache-v12-004.json)。四批共40镜／163秒／4890帧，输出、比较日志及完整24fps源片均保留，仍须全部48镜正式导入和成片检查。

剩余S40—S48另有[局部证据准备进程](../series/vivhite/autumn-journey/episodes/01-autumn-journey/production/S40-S48-local-print-detail-preparer-v12.py)，实际运行代码的相同字节已入库，见[启动及绑定记录](../series/vivhite/autumn-journey/episodes/01-autumn-journey/production/S40-S48-local-print-detail-preparation-v12.json)。它每60秒只检查本地下载结果，核对既定任务、输入、源片及完整解码报告，再提取各镜周边图案；片尾则导出完整336帧的蓝蝶原生局部。不请求HTTP、不改视频、不改变渲染队列，不自动给出画面通过结论。区域坐标来自实际768P输入首帧，未来4K若移动或出裁切边界，必须另行扩大检查；手部与多窗口接缝仍由后续实际画面审阅处理。启动记录只证明进程开始等待，不证明待生成镜头已经检查。

北京时间16:13，S40／S41材料与实际审阅已完成；本地日志显示服务端先运行S48，S42—S47仍等待。旧整景／候选及局部两个准备循环都按镜号等待，会使先完成的片尾继续等前面的镜头。现用[按完成顺序准备材料的程序](../series/vivhite/autumn-journey/episodes/01-autumn-journey/production/prepare-ready-native-evidence-v12.py)接替剩余S42—S48：每60秒检查全部本地待办，哪段下载和完整解码绑定先齐就先导出整景、全部原生候选和既定周边局部。原区域、源片和检查程序保持绑定；准备成功仍不代表实际看过或采用。

只停止了两个旧材料观察器的四个Python父／子进程，并保存原代码、日志及最后状态；两组生成客户端／控制器的进程身份、配置和全部49份已提交任务／请求指纹均实际复核未变。新进程以隐藏窗口独立运行，旧版本保留，不调用HTTP或重新排队。启动与实测范围见[部署记录](../series/vivhite/autumn-journey/episodes/01-autumn-journey/production/ready-order-native-evidence-preparation-v12.json)。[三项回归检查](../series/vivhite/autumn-journey/episodes/01-autumn-journey/production/test_prepare_ready_native_evidence_v12.py)验证后号片尾不被前号排队镜头挡住、任务错绑拒绝，以及报告未齐时等待／源片改变时拒绝；当前七份真实待办也完成只读绑定预检，未伪造未来画面通过。

后续只可在全部48镜通过正式导入后，把与导入源片SHA-256、原定30fps帧数、尺寸及配方完全一致的缓存和收据复制到新合成目录的`segments/`，由`local_video_finisher.py`再次核验。缓存不能代替最终实际素材的人格／披露绑定检查，也不能将源片审核冒充编码成片、音轨或字幕审核。运行进程独立于对话，日志及启动指纹保留在原4K运行目录；渲染守护和服务端队列配置不变。

## 2026-11-18实际故障与修复

北京时间08:50:30，客户端替换`jobs/S04.json`时发生Windows `WinError 5`，留下完整`.partial`记录后退出。旧控制器只自动恢复网络错误，漏掉了本地JSON替换失败，因而停在`attention-required`。S04仍在服务端继续运行，09:26左右完成；此后GPU队列未被继续推进，直至13:19本次直接检查时恢复。不能把这段空转描述成持续正常渲染。

本次保留旧状态、失败临时文件、控制器配置及原任务，归档于运行目录的`recovery-history/20261118-atomic-json-sharing-failure/`。修复为每个JSON写入使用独立临时文件，对Windows短暂拒绝替换（5／32／33）进行最多10次退避重试；持续失败时保留新旧记录并抛错。控制器仅对明确的JSON临时文件替换错误恢复，仍禁止重复提交受理不明的POST、失败或取消任务。

实际Windows测试用打开的读取句柄阻止文件替换，稍后释放后成功保存；另验证持续拒绝时有界失败、不覆盖其他临时记录，以及本地错误恢复不会绕过受理不明限制。已部署冻结版本004，13:19:47下载同一S04原任务，13:20:41正常提交S05，没有重做S04或改变已提交计划。

后台守护仅作兜底。助手连接期间直接核对真实队列、任务日志、下载文件与质量证据，发现守护缺陷就修复。[本次恢复收据](../series/vivhite/autumn-journey/episodes/01-autumn-journey/production/recovery-v11-4k-20261118.json)及[阶段审计](../series/vivhite/autumn-journey/episodes/01-autumn-journey/production/quality-audit-v11-4k.md)分别记录运行恢复与实际画面结论。

S03原画修复实际复审后，另部署005以支持已审核的修订源片选择。只替换控制器，续接同一004客户端PID `13016`与同一S05服务端任务，生成进程未停止。技术预览对修订文件、原始父文件、修订收据、完整帧检查和实际通过结论逐一绑定；原始问题源片不会被修订文件覆盖。修改选择后不能静默复用旧预览缓存，源片选择在合成中变化则保留中间文件并报错。

14:57另修复控制器自身的完成判定：旧代码只匹配预览文件哈希，可能在素材选择或制作绑定改变后仍把旧预览判为完成并关闭兜底。现在还核对源计划、当前素材选择指纹、音乐、字幕、3840×2160／30fps／6150帧／205秒及完整解码收据。相关7项恢复与完成判定测试通过；这是技术预览有效性检查，不授予内容通过结论。

修复部署为006；只更换经过路径核对的旧守护进程，新守护PID `129376`续接同一客户端PID `13016`及其创建时间，服务端S06任务ID保持不变。归档在`recovery-history/20261118-preview-completion-binding/`。S05完整源片120帧已实际审阅通过，14:38:43提交S06，15:00前后仍在正常计算；所有镜头时长和模型参数均保持已提交计划。

15:36按用户新要求部署007：客户端旧逻辑把4K推理单窗口误当成只能排一个HTTP任务，已解除这一排队限制。新客户端保留S06既有服务端任务，补入S07、S08、S09，实际队列已核对为1个运行＋3个等待，轮询间隔60秒。为应用参数，只重启本机轮询客户端；没有取消或重做服务端推理。守护继续作为兜底，助手主要处理出片审核、修订和异常，不再反复查询或汇报模型块数。

17:03按用户“尽可能将剩余任务全部排队”的后续要求部署008。核实服务端同模型未完成任务上限为32后，扩大客户端预排窗口至32，实际为S07运行、S08–S38共31镜等待；S39–S48随空位补入。保留所有既有任务ID及计划字节，未取消服务端推理。批量轮询合并读取等待队列，429只作为明确未受理的退压信号，停止本轮后续新提交并继续下载已完成任务。冻结007及旧配置保留于恢复历史；新代码、配置和PID绑定另行记录，不热改运行快照。

11月19日04:10:55，查询队列时出现一次`WinError 10060`连接超时。控制器008自动接续新客户端，S16仍使用原任务ID，随后本地记录继续更新为`in_progress`；47份已提交请求的哈希与原生4K参数重新核对。旧客户端日志、完整请求及所有视频保留，没有取消或重新提交S16。此次没有更新冻结渲染程序。

助手的旧本地监听脚本把短暂的`started-generation`状态误判成异常而退出，已用[独立本地事件监听器](../series/vivhite/autumn-journey/episodes/01-autumn-journey/production/watch-local-source-v11.py)修复并恢复实际S16监听。它只读本地文件，每20秒检查一次，不增加HTTP查询，不提交、取消或自动批准镜头。新鲜启动及重试状态最多容忍360秒，心跳过期180秒、持续不可读超过180秒、实际需检查状态均会报警；已完成且指纹匹配的源片先于正常控制器收尾状态处理。源码及[5项恢复边界测试](../series/vivhite/autumn-journey/episodes/01-autumn-journey/production/test_watch_local_source_v11.py)入库，完整收据见[本次监听修复记录](../series/vivhite/autumn-journey/episodes/01-autumn-journey/production/local-watch-recovery-v11-4k-20261119.json)。

```powershell
video-maker/.venv/Scripts/python.exe -X utf8 series/vivhite/autumn-journey/episodes/01-autumn-journey/production/watch-local-source-v11.py `
  --directory D:/workspace/vivhite-analysis-output/vivhite/autumn-journey/production-v11-native-4k-001 `
  --shot S16
```
