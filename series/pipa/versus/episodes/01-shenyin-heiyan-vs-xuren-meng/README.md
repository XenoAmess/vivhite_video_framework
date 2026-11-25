# 《琵琶曲》神隐黑炎 vs 虚人梦

当前交付为两张独立的全身角色概念图。图像采用同一画布尺寸、近正面自然站姿和浅灰背景，可并排对照或单独用作图像参考。

| 角色 | 入库概念图 | 造型要点 |
| --- | --- | --- |
| 神隐黑炎 | [全身 PNG](assets/generated/character-concepts-v2/shenyin-heiyan.png) | 保留原图的深棕短发、蓝灰眼、深蓝金边立领与金色流苏肩章。参考法国第一帝国军服延伸出收腰长尾军礼服、浅色马甲和贴身马裤、黑色长靴。 |
| 虚人梦 | [全身 PNG](assets/generated/character-concepts-v2/xuren-meng.png) | 保留金发红眼、深红兜帽披风、赭金内衬、几何镂空和左肩侧面具。双手空出，披风收近身体并离地。 |

第二轮通过生成时交叉引用两人的全身图，统一身高、头身比及修长身材。并排核对眼线、下颌、肩腰、手腕和脚底。两张图均为内置 imagegen 直接输出的 1024×1536 PNG，采用原始文件字节入库。 [实际提示词与输入顺序](assets/generated/character-concepts-v2/generation-requests.json)

神隐黑炎的军服补全部分参考法国第一帝国的长衣摆、马裤和靴型，照顾原图已有的深蓝和金色装饰。 [法国军事博物馆近卫军制服资料](https://www.musee-armee.fr/fileadmin-cru-1503318930/user_upload/Documents/Support-Visite-Fiches-Objets/Fiches-periode-napoleon/MA_grenadier-garde-imperiale.pdf) · [拿破仑基金会军服简介](https://www.napoleon.org/en/young-historians/napodoc/napoleons-grande-armee-2/)

后续分镜中，神隐黑炎对应夸张开枪的一方，虚人梦对应拍屁股挑衅的一方。动画参考为 Kotte Animation 原片，重点分镜和配乐参考「成都超人 p01 原曲」。 [原动画素材 BV1pvY16QEwd](https://www.bilibili.com/video/BV1pvY16QEwd/) · [重点分镜与 BGM BV14BeA6CEUb](https://www.bilibili.com/video/BV14BeA6CEUb/)

首轮 S01 技术样片为单镜 5 秒、1344×768、24 fps（120 帧），配乐取指定参考片 00:24–00:29 的原混音。合成文件和完整运行记录保存在仓库外。两位角色的造型和同框比例可辨，虚人梦的转身与披风摆动可见，拍击和后退动作幅度偏小。 [生成、素材指纹与全帧检查收据](production/sample-S01-768p-001.json)

完整版本使用按帧复核后的 48 镜，各镜分别投喂本地模型、分别验收，最后拼接并合成指定 BGM。 [全片计划、执行与验收清单](production/execution-and-review.md)
