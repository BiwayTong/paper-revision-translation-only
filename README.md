# Turnitin 蓝色高亮 · 苹果翻译

准备 Turnitin 报告 PDF 和送检时的英文 Word 原稿。这个版本按报告定位标蓝的字句，再把定稿写回对应位置。如果手头只有编号摘录，可以先修订，找到匹配的 Word 底稿后再回填。

[下载本版 ZIP](https://github.com/BiwayTong/paper-revision-translation-only/releases/latest/download/turnitin-highlight-revision-translation-only.zip) · [查看其他三个版本](https://github.com/BiwayTong/paper-revision-translation-only#选一个版本)

## 安装和使用

1. 解压 ZIP，把 `turnitin-highlight-revision-translation-only` 整个目录放进 `~/.codex/skills/`。如果自定义了 `CODEX_HOME`，则放进该目录下的 `skills/`。
2. 打开新的 Codex 会话，附上两份文件，输入下面的请求。

> 用 $turnitin-highlight-revision-translation-only 提取报告标蓝的句子，跑完三轮翻译，只把必要的修改放回 Word。请保留引用，给我定稿和过程稿。

自动运行需要在 macOS「快捷指令」中准备两条使用苹果「翻译文本」动作的指令，分别指定英译中和中译英。PDF 高亮定位和 Word 回填使用 Python、pdfplumber 和 lxml。 [配置、操作与断点恢复](references/operations.md)

## 三轮之后

每轮保留工具返回的中文和英文原文，以及核对后的两份稿件。下一轮承接上一轮英文稿。最后按原意做最小校对，交付Word 副本、编号摘录、过程稿、段落对照、修改记录与正文词数。

如需通过 Git 安装这个分支，可运行以下命令。

```sh
git clone --branch turnitin-highlights --single-branch https://github.com/BiwayTong/paper-revision-translation-only.git ~/.codex/skills/turnitin-highlight-revision-translation-only
```
