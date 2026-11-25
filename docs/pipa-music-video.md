# 《琵琶曲》双角色视频制作调研

建议先定一条可用于成片的琵琶录音，再用两张角色图设计镜头。第一轮做一个 5 秒双人中景和一个 5 秒单人演奏镜头，分别验证两人同框和手指接触琴弦。这里暂按两张图对应两位不同角色、A 演奏、B 聆听规划。实际角色分工、曲目、录音与叙事随素材确定。

## 两张图如何使用

- **双人镜头**把 A 和 B 两张图依次传入 `image_reference`。用 `<Picture 1>` 和 `<Picture 2>` 分别标注角色，写清各自的外观特征、在画面哪边、做什么。首轮只安排 A 做一个清楚的演奏动作，B 保持坐姿并看向 A。若同框时外观互串，可先准备一张经审阅的双人构图图，用它约束机位、站位和琴的位置。 [FastH3 Omni 参考图提示方法](https://www.reactor.inc/learn/fast-h3-omni-prompting)
- **单人镜头**只传该镜出场角色的图，提示词按该次请求的图片顺序编号。演奏镜头优先用固定斜侧中近景，同时看见琴颈、左手按弦、右手拨弦和琴身支撑点。试听段选择慢拍、容易观察起音的乐句，便于找到手指触弦与音头错位的位置。 [东京艺术大学琵琶右手示范](https://koizumi.geidai.ac.jp/asia/jp/han/pipa/000132.html) · [现代琵琶的四弦结构与左右手动作](https://omeka-s.grinnell.edu/s/MusicalInstruments/item/1812)
- **需要清楚看见指法的镜头**可自行拍摄同一录音对应的短演奏视频，或使用获授权的素材。将它作为 `video_reference` 的 `<Video 1>`，在相近机位引导动作；角色外观仍来自照片。需要逐音对应时，手部特写宜直接使用可用的实拍演奏镜头，或使用有指法关键帧控制的角色动画。教程可用于比对弹挑、轮指等动作；原片能否纳入成片取决于其授权。 [FastH3 Omni 多模态输入](https://nuvalab.ai/fasth3/) · [史密森尼吴蛮琵琶演奏与技法](https://asia-archive.si.edu/podcast/master-of-the-chinese-pipa-wu-man-2/)

## 随录音安排镜头

先标出乐句边界、显著拨弦音头与尾音结束点，根据实际录音定剪辑时码。以下为起稿顺序，段长由录音决定。

| 录音位置 | 画面 | 检查点 |
| --- | --- | --- |
| 开场及第一音 | 双人中景交代座位、朝向和琴，切到 A 起手 | 人物对应参考图，左手在指板，右手落在弦区 |
| 清楚的慢速乐句 | 固定斜侧机位拍单人演奏，留两手和完整琵琶 | 琴身和四根弦形态稳定，拨弦时手指接触弦，关键音头对得上 |
| 快速轮指或乐句过门 | 用真实演奏近景显示要辨认的指法，或切 B 的反应、双人远景及环境 | 同一段录音连续，B 的视线方向和两人座位连续 |
| 尾音 | 回双人中景，演奏动作收住，到尾音结束再切出 | 画面和录音收束点一致 |

Omni 可接受一小段 `audio_reference` 作节奏引导。用 `<Audio 1>` 指出它对应哪一段演奏；对比生成结果与录音中的音头后再选片。正式剪辑以完整的原录音作时间轴，生成音轨另存用于对照。试镜先用 1344×768、24fps。需要 4K 时，从实际选用且已经审阅的源片再生成，并重新检查琴弦、指尖接触和音头时序。 [FastH3 Omni 音频参考说明](https://www.reactor.inc/learn/fast-h3-omni-prompting) · [本仓库原始768P与原生4K规约](local-video-768p-4k.md)

## 局域网试镜请求

实际制作时，先确定本期角色并按仓库规约审核计划、两张角色图、可选动作参考及实际录音，再上传审核通过的素材。按图 A、图 B 的顺序把 `POST /v1/files` 返回的 `file_id` 填入下例，然后向 `http://192.168.1.11:8080/v1/videos` 提交。下例采用角色代号，外观描述随实际图片补齐。 [角色与文案审核规约](character-workflow.md) · [统一模型服务的媒体字段](https://github.com/XenoAmess/local-model-operations/blob/main/deployments/video-generation/docs/unified-model-service.md)

```json
{
  "model": "fasth3-omni-bf16",
  "task": "ref2va",
  "size": "1344x768",
  "seconds": 5,
  "num_inference_steps": 8,
  "guidance_scale": 1.0,
  "seed": 1234,
  "image_reference": [
    {"file_id": "file_角色A"},
    {"file_id": "file_角色B"}
  ],
  "prompt": "固定斜侧双人中景，单一连续镜头。<Picture 1> 的角色A坐在画面左侧，怀抱梨形四弦琵琶，琴身靠在腿上，琴颈斜向上。左手指尖贴住琴颈上的一根弦，右手食指在琴身上方拨这根弦一次，再停住。<Picture 2> 的角色B坐在画面右侧，安静看向A。保持两张参考图各自的发型和服饰，两人位置稳定，镜头内可见A的双手和整把琴。"
}
```

有匹配乐句的动作或音频参考时，可分别加入 `video_reference`、`audio_reference` 列表，元素同样为 `{"file_id":"…"}`。提交后保存实际请求与完整任务 ID，查终态并下载原片。选镜时结合全段回放与逐帧局部检查，记录衣着与身份、双手和琴弦、动作和音头，以及内容审核覆盖。现有旅行视频入口的计划校验包含该项目特定的角色和镜长约束；上面的 JSON 是统一服务请求示例。两张人物图和实际录音尚未提供，本次调研以验证服务和制定试镜方案为止。 [局域网媒体请求、时长与参考字段](https://github.com/XenoAmess/local-model-operations/blob/main/deployments/video-generation/docs/video-http-api.md)
