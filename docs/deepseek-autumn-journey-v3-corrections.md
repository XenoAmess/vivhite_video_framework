# 大肥鱼旅行v3：稳定实体包与实际挪动玩偶

用户继续指出v2的2:28／2:31袋上图案错位、3:07玩偶只是颠动。此前助手检查不能覆盖用户反馈。两段旧源片和全部候选保留，另建v3，不改其他46镜、48镜时间、配乐、标题和献词；目标205秒／6150帧。

## 先改变导致修复失败的动作条件

S37的变形布袋不能仅用少量四边形锚点当作刚性平面；即使图案本身不眨眼，整张印花仍可能相对缝线滑动。v3重新用imagegen制作田边停步的构图，包稳放木栏，手与包分开。其后处理对象是完整实体包：外轮廓、四角、拉链、织物与印花一同保留；定位依据是独立木栏，不是图案中的眼睛或头发。

该路线限于可靠支撑、几乎刚性的周边和轻微镜头运动。若人手跨过包、布面大折叠、包转面或载体跟踪失效，不能扩大容差强行拼贴。整包固定不等于整幅画面冻结，仍要检查环境、衣料、自然动作及合成边界。具体输入、参数与实际决定由本期v3后期计划和源片审核分别绑定，不因本页写出方案自动判通过。

实际生成的后半段，手指仍然伸近并接触了袋边。首组整包合成把指尖截断，虽已编码成`production-v3-768p-full-001`，在原生成片4530帧复核时发现并拒收，未发布。仅看开头和结尾或只看缩略整景，仍可能漏掉中途遮挡问题。

最终第二组在限定手部区域内恢复**同一原视频、同一帧的真实原手像素**，让原手自然挡在完整包前方，不生成新手，不把另一帧的手贴过来。入口为[原遮挡恢复](../video-maker/tools/restore_original_occlusion.py)与[正式输入审核门](../series/deepseek/autumn-journey/episodes/01-autumn-journey/production/render-hand-protected-pouch-v3.py)。肤色阈值只用于本镜限定区域，不是通用人物分割；仍需全帧检查指尖、包边和木栏接触。实际输出在120帧整景、120帧原生包／手局部和96／119原生整景复核后另开`full-002`装片，旧候选不覆盖。

## 用椅面作为玩偶是否挪动的参照

S47沿用原首帧重新生成，提示词要求整体沿椅面向左滑移，底部不离开支撑，完成后松手并留在新位置。不是要求脸、四肢或尾巴单独活动，也不是把视频上下颠动解释为“摆正”。

已实际查看新源片全部120帧整景和120帧玩偶／手部图册，并查看原生0、72、96帧。双手推动整个玩偶向左，松开后玩偶保持新位置；没有再放回起点。源片5秒，正式入片仍取前4秒，后1秒只是保留的源材料。

[相对运动诊断](../video-maker/tools/measure_prop_motion.py)分别估计完整玩偶和椅面的运动，把玩偶位置转换回椅面坐标，避免把相机移动当成挪动物体。采用片段末帧对应原生95帧，水平位移约−157.1像素、垂直约0像素，最后使用的一秒水平范围约1.74像素。这是实际图像坐标诊断，不是8–10厘米的物理实测，不替代手腕、支撑和玩偶形状审图。

[诊断测试](../video-maker/tools/test_measure_prop_motion.py)覆盖相机运动抵消、相机变换下的左移、上下颠动不产生水平位移三种情况。程序不输出语义通过；完整实际证据见[位移记录](../series/deepseek/autumn-journey/episodes/01-autumn-journey/production/prop-motion-v3-S47.json)与[玩偶源片审核](../series/deepseek/autumn-journey/episodes/01-autumn-journey/production/source-review-v3-plush01.json)。

## 复用入口与审核边界

- [本轮要求](../series/deepseek/autumn-journey/episodes/01-autumn-journey/production/revision-v3-requirements.md)、[新首帧／提示词](../series/deepseek/autumn-journey/episodes/01-autumn-journey/assets/generated/production-v3-firstframes-001/README.md)。
- [完整实体载体合成](../video-maker/tools/stabilize_carrier_plane.py)，不修改已绑定的旧worker和计划。
- [逐帧整景与局部检查图](../series/deepseek/autumn-journey/episodes/01-autumn-journey/production/prepare-source-proof-v3.py)、[整包原生像素图册](../series/deepseek/autumn-journey/episodes/01-autumn-journey/production/prepare-native-pouch-proof-v3.py)。图册生成不自动给出通过决定。
- [独立v3装配器](../series/deepseek/autumn-journey/episodes/01-autumn-journey/production/assemble-reviewed-film-v3.py)只接受S37／S47两处有实际全源帧决定的替换，逐项核对48镜的原始起点和长度，其他46镜转移精确字节相同的已有决定。实际制作计划及素材必须通过人格／披露绑定后才能正式装配。

助手有序审图、完整机器解码、人工连续播放及用户审美验收分别记录，不能把其中任何一项称作另一项。新旧音频、字幕和时长要从实际成片核对，不能只看计划上的205秒。
