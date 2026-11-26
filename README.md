# 普通论文 · Google 翻译

准备英文 Word（`.docx`）、UTF-8 文本或粘贴的正文。可以处理全文，也可以指定章节、段落或句子。

[下载本版 ZIP](https://github.com/BiwayTong/paper-revision-translation-only/releases/latest/download/google-translate-paper-revision-translation-only.zip) · [查看其他三个版本](https://github.com/BiwayTong/paper-revision-translation-only#选一个版本)

## 安装和使用

1. 解压 ZIP，把 `google-translate-paper-revision-translation-only` 整个目录放进 `~/.codex/skills/`。如果自定义了 `CODEX_HOME`，则放进该目录下的 `skills/`。
2. 打开新的 Codex 会话，附上或粘贴稿件，输入下面的请求。

> 用 $google-translate-paper-revision-translation-only 只修订 Discussion 章节，跑完三轮翻译。尽量保留我的措辞和引用，给我 Word 定稿和过程稿。

可用 Google 翻译网页，无需 API Key。需要自动调用时，使用已启用 Cloud Translation API 的项目，并配置 API Key 或应用默认凭据。Word 回填使用 Python 和 lxml。 [配置、操作与断点恢复](references/workflow.md)

## 三轮之后

每轮保留工具返回的中文和英文原文，以及核对后的两份稿件。下一轮承接上一轮英文稿。最后按原意做最小校对，交付英文定稿、过程稿、段落对照、修改记录与正文词数。

如需通过 Git 安装这个分支，可运行以下命令。

```sh
git clone --branch google-translate --single-branch https://github.com/BiwayTong/paper-revision-translation-only.git ~/.codex/skills/google-translate-paper-revision-translation-only
```
