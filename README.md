# 论文轻校对

这两套 Codex 工具都支持用苹果翻译或 Google 翻译做三轮英中往返，保留每轮原始译文，尽量沿用作者原句。

**论文轻校对**完成三轮翻译后，对照原意、修正必要问题。想在第三轮英文回译后再用 Humanizer 复核一次措辞，可选[论文轻校对·表达复核](https://github.com/BiwayTong/apple-translate-paper-revision)。

若想只装一个技能，按次选择翻译工具、修改范围和表达复核，请看[论文轻校对·通用版](https://github.com/BiwayTong/paper-proofread)。在其他 AI 对话里也可以直接[复制通用提示词](https://github.com/BiwayTong/paper-proofread/blob/main/PROMPT.md)。

## 选一个版本

| 你要修订的内容 | 翻译工具与分支 | 安装包 | 操作指南 |
| --- | --- | --- | --- |
| 全文、章节或自选段落 | [苹果翻译](https://github.com/BiwayTong/paper-revision-translation-only/tree/main) | [下载 ZIP](https://github.com/BiwayTong/paper-revision-translation-only/releases/latest/download/apple-translate-paper-revision-translation-only.zip) | [稿件选区与回填](https://github.com/BiwayTong/paper-revision-translation-only/blob/main/references/workflow.md) |
| 全文、章节或自选段落 | [Google 翻译](https://github.com/BiwayTong/paper-revision-translation-only/tree/google-translate) | [下载 ZIP](https://github.com/BiwayTong/paper-revision-translation-only/releases/latest/download/google-translate-paper-revision-translation-only.zip) | [稿件选区与回填](https://github.com/BiwayTong/paper-revision-translation-only/blob/google-translate/references/workflow.md) |
| Turnitin 标蓝的字句 | [苹果翻译](https://github.com/BiwayTong/paper-revision-translation-only/tree/turnitin-highlights) | [下载 ZIP](https://github.com/BiwayTong/paper-revision-translation-only/releases/latest/download/turnitin-highlight-revision-translation-only.zip) | [高亮定位与回填](https://github.com/BiwayTong/paper-revision-translation-only/blob/turnitin-highlights/references/operations.md) |
| Turnitin 标蓝的字句 | [Google 翻译](https://github.com/BiwayTong/paper-revision-translation-only/tree/turnitin-highlights-google) | [下载 ZIP](https://github.com/BiwayTong/paper-revision-translation-only/releases/latest/download/turnitin-highlight-google-revision-translation-only.zip) | [高亮定位与回填](https://github.com/BiwayTong/paper-revision-translation-only/blob/turnitin-highlights-google/references/operations.md) |

**苹果翻译**通过 Mac 上的两条快捷指令自动运行，分别用于英译中和中译英。**Google 翻译**可以使用免 API Key 的网页方式，或使用已启用 Cloud Translation API 的项目自动运行。

## 在 Codex 中使用

1. 下载所选版本的 ZIP 并解压。把里面含有 `SKILL.md` 的整个目录放进 `~/.codex/skills/`，保留目录名。如果自定义了 `CODEX_HOME`，则放进该目录下的 `skills/`。
2. 打开新的 Codex 会话。普通论文版可附上 Word（`.docx`）、UTF-8 文本或直接粘贴英文。高亮版请附上报告 PDF 和送检时的英文 Word 原稿。
3. 输入 `$` 加上安装目录名，再写明修改范围。下面是两个可以直接使用的例子。

**普通论文 · 苹果翻译**

> 用 $apple-translate-paper-revision-translation-only 只修订 Discussion 章节，跑完三轮翻译。尽量保留我的措辞和引用，给我 Word 定稿和过程稿。

**蓝色高亮 · Google 翻译**

> 用 $turnitin-highlight-google-revision-translation-only 提取报告标蓝的句子，跑完三轮翻译，只把必要的修改放回 Word。请保留引用，给我定稿和过程稿。

## 会收到什么

每轮先英译中，按需要核对中文，再译回英文。第二、三轮从上一轮核对后的英文开始。第三轮结束后直接对照原意并做最小校对。如果只是同义替换，定稿沿用作者原句。

交付包括另存的英文定稿、三轮原始译文与调整稿、段落对照、修改记录和注明统计口径的正文词数。蓝色高亮版另附带编号的摘录，方便对照报告核对位置。

本页对应普通论文苹果翻译版。需要通过 Git 安装这个版本时，可运行以下命令。

```sh
git clone --branch main --single-branch https://github.com/BiwayTong/paper-revision-translation-only.git ~/.codex/skills/apple-translate-paper-revision-translation-only
```

四个版本也可从同一发布页下载。[全部安装包与版本记录](https://github.com/BiwayTong/paper-revision-translation-only/releases)
