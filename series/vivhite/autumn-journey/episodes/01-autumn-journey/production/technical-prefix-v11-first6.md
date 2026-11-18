# 前六镜原生 4K 技术预览

本次仅拼接已完成并经助手逐帧审阅的 S01–S06，检查实际编码、片头文字、配乐排程及镜头衔接。文件为运行目录下 `checkpoints/prefix-06-001/film-unreviewed-prefix.mp4`，不是完整成片，也没有发布为正式 Release。完整影片仍要求 205 秒、6150 帧。

预览为 3840×2160、30fps、23 秒、690 帧；六镜沿用原计划的 4、3、4、3、5、4 秒。S03 使用已复核的徽章恢复 v2，S06 使用已复核的眼睛恢复 v2，其余使用对应原生 4K 源片。原始生成结果及失败候选均保留。音乐仍是原 WAV 的前 23 秒，舍弃模型音轨；片名沿用原 ASS 的文字、字体、位置、渐显和渐隐。技术预览末尾没有额外添加全画面淡出，也不改变正式片尾。

运行入口为 [render-reviewed-prefix-v11.py](render-reviewed-prefix-v11.py)，参数如下。配置保存在本机运行目录，不进 Git。

```powershell
video-maker/.venv/Scripts/python.exe -X utf8 series/vivhite/autumn-journey/episodes/01-autumn-journey/production/render-reviewed-prefix-v11.py `
  --configuration <运行目录>/metadata/durable-controller-config.json `
  --count 6 --destination <运行目录>/checkpoints/prefix-06-001 `
  --technical-prefix-only
```

入口核验冻结配置、未修改的完整生成计划及实际 48 份生成输入的人格审核绑定，并要求所含源片具有匹配哈希、全部原生帧审阅和七项通过记录。此检查不替代最终所选 4K 素材及完整影片的人格一致性、信息披露复审。段落按原时长正常取用并转为 30fps，不插值或拉伸动作时间。

本次完成全量音视频解码，并逐帧比较全部 690 个编码画面与拼接画面：已知标题区域之外最低 PSNR 为 41.472dB，低相似度帧为 0。人脸检测覆盖全部 690 帧，报告四个候选帧；助手逐一查看原生裁剪及上下文，分别为 S04 钥匙扣印刷角色、S05 前轮轴心部件、S06 连续两帧的贴纸印刷角色，未发现真人脸。

助手另检查六镜中点总览、全部候选证据、标题出现前/渐显/完整显示/渐隐以及预览最后两帧对应的导出图。此处编码后语义复核是选帧复核；源片另有全部 120 帧整景及周边/手部细节检查。没有将机器逐帧比较等同于助手逐帧看完全部 690 个编码画面，也没有声称人工连续播放或用户审美验收。标题文字和音乐哈希与原配置一致；尚未进行听感验收。

另将预览中实际 AAC 解码为 48kHz 双声道浮点 PCM，与原 WAV 前 23 秒逐样本零偏移比较：每声道有效覆盖 1,104,000 个采样，左右相关系数分别约 0.99999402／0.99999400，信号与差值之比 49.17dB。AAC 解码多出的 896 个采样是编码对齐尾部，未计入有效比较区；音轨和容器时长仍是 23 秒。此检查支持音乐内容及排程一致，不等于听感验收。比较收据原件保存在预览目录 `audio-comparison.json`。

详细哈希、覆盖范围及候选解释见 [technical-prefix-v11-first6.json](technical-prefix-v11-first6.json)。所有导出图片保存在本期 `assets/generated/production-v11-native-4k-001/review/prefix-06-001/` 并纳入 Git；媒体、编码分段、日志及完整机器检查报告保留在外置运行目录。
