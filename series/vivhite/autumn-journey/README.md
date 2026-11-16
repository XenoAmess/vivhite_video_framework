# 白绮／秋日旅程

本目录是内容子项目，沿用“系列／课题／期”的组织方式。

当前[导演案 v6](episodes/01-autumn-journey/director-v6.md)以无对白的多地点旅行蒙太奇展示白绮在多彩世界中的自由旅行；按用户最新指示恢复48镜，总长196秒，S20为一个连续10秒高山湖长镜，其余47镜2–5秒。此前两个5秒湖景及导演案v5归档保留。正在使用BF16 FastH3、36层解码器制作1344×768版，其后逐镜调用本地2K接口制作2560×1440版，尚未交付新成片。真实感人物以手、衣袖、腿脚等不露脸局部，与白绮贴纸、玩偶、周边及意象同框。沿用已修订的普通真实世界场景，保留自然天气、合理植被与日常设施。

制作补充：所有出场人物均为女性，女性化服装贴近白绮设定图；静默、不露脸与短镜头要求适用于成片全部帧。原图中没有的无关人员，即使不露脸也拒收。

最新[片尾修订 v4](episodes/01-autumn-journey/production/production-v4.md)将 S48 蓝蝶放慢到原速的 1/8，天空只显示“白绮|秋日旅程”和“献给最可爱的你”，不显示制作署名。完整影片与单独片尾已另存；原 v3 成片与导演稿保持归档，新片尾以[合成计划 v5](episodes/01-autumn-journey/final-assembly-plan-v5.json)为准。

- 主人公：白绮，英文名 Vivhite；角色 ID 为 `vivhite`。
- [第一期清单](episodes/01-autumn-journey/episode.json)。
- [当前导演案 v6](episodes/01-autumn-journey/director-v6.md)、[两段湖景版v5](episodes/01-autumn-journey/director-v5.md)与[历史导演案 v3](episodes/01-autumn-journey/director.md)。
- [周边与图像生成说明](episodes/01-autumn-journey/image-briefs.md)。
- [背景音乐实际生成方法与复现](../../../docs/autumn-journey-music-generation.md)。
- [参考导演案](../../../docs/analysis/BV1nB3u6tEHD/director.md)。

周边母版、场景参考图和全部保留版本已保存到项目并提交 Git；[生成计划](episodes/01-autumn-journey/production-plan-v4.json)用于本地 Ref2VA 视频渲染。[美术修订记录](episodes/01-autumn-journey/production/realism-revision-001.md)解释真实世界的调整。成片为 202 秒／48 镜／1080p30，具体选片、声音、失败版本与审阅范围见[制作记录](episodes/01-autumn-journey/production/production-v3.md)及[最终合成计划](episodes/01-autumn-journey/final-assembly-plan-v4.json)。周边是生成图像中的拟制设计，未生产实物。用户提供的 `character.zip` 共 11 张图已逐张查看；[素材清单](episodes/01-autumn-journey/reference-assets.json)记录版本与用途，原图留在公开仓库外。

导演案、图像说明和实际视频生成计划分别进行助手语义审核。公开收据位于本期 `reviews/`，详细依据只存私有角色库。每份收据仅覆盖其文件和实际绑定素材，不自动批准后续生成视频；新素材和最终声音／标题合成须另审。
