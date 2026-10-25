# vivhite_video_framework

以 Java 为主要开发语言，包含自动化数学科普视频制作器和视频分析器两个子项目。分析器提炼参考视频的创作方法，制作器据此制作和优化视频。

## 项目结构

根目录 `pom.xml` 同时作为 Maven 父 POM 与聚合 POM，统一管理 Java 版本、编码和构建插件版本。两个子项目分别拥有自己的目录、POM 和源码。

| 子项目 | 职责 | Java 包前缀 |
| --- | --- | --- |
| [video-maker](video-maker/README.md) | 自动制作数学科普视频，完成选题、数学内容核验、文案、分镜、视听素材及合成渲染 | `com.xenoamess.vivhite_video_framework.maker` |
| [video-analyzer](video-analyzer/README.md) | 读取视频，结合本地分析与 GPT 分析，解读主题、分镜、文案和创作风格，提供可执行的制作建议 | `com.xenoamess.vivhite_video_framework.analyzer` |

- 父 package / Maven groupId：`com.xenoamess.vivhite_video_framework`。
- 父 artifactId：`vivhite-video-framework`；当前版本：`0.1.0-SNAPSHOT`。
- 两个子项目通过带版本标识的分析报告交换信息，目前不互相添加 Maven 依赖。
- 分析报告应将时间戳、关键帧和文案等证据，与风格参数、逐镜头建议及优化动作对应起来，支持制作器模仿创作方法并验证改进效果。

当前已建立可构建的模块骨架及职责约定；视频制作、本地分析、GPT 接入和报告格式尚待实现。

## 构建与验证

需要 JDK 21 或以上版本，编译目标为 Java 21。仓库提供 Maven Wrapper，固定使用 Maven 3.9.16，无需额外安装 Maven；首次执行需联网下载 Maven 和构建插件。

Windows PowerShell：

```powershell
.\mvnw.cmd clean verify
.\mvnw.cmd -pl video-maker -am verify
.\mvnw.cmd -pl video-analyzer -am verify
```

macOS / Linux：

```sh
./mvnw clean verify
./mvnw -pl video-maker -am verify
./mvnw -pl video-analyzer -am verify
```

第一条命令构建并验证全部模块，后两条分别选择单个子项目及其所需的上游项目。子项目采用 Maven 标准源码布局；后续测试放在各自的 `src/test/java` 中。当前尚无测试用例或可运行的应用入口，构建产物位于各子项目的 `target/` 下。

## 开发约定

- 主要语言：Java。
- 文件编码：UTF-8；Java 代码使用 4 个空格缩进。
- Java 版本、公共依赖版本及构建插件配置在父 POM 中统一维护；子项目仅声明自身需要的依赖。
- 自动化协作规范见 [AGENTS.md](AGENTS.md)。完成有文件变更的任务后，默认检查、Git 提交并推送。

## 许可证

本项目采用 GNU General Public License v3.0，SPDX 标识为 `GPL-3.0-only`。完整协议见 [LICENSE](LICENSE)。

Maven Wrapper 脚本保留 Apache License 2.0 授权，协议见 [.mvn/wrapper/LICENSE](.mvn/wrapper/LICENSE)。
