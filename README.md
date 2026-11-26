# 普通论文 · 苹果翻译基础版

附上英文 Word、UTF-8 文本或直接粘贴正文，可以指定全文、章节或段落。 每轮用苹果翻译将英文译成中文，再将核对后的中文译回英文。连续三轮都保留原始译文，下一轮承接上一轮的英文稿。第三轮回译直接进入对照和最小校对。回译只带来同义替换时，定稿沿用作者原句。

## 选择版本

| 修改范围 | 翻译工具 | 分支 |
| --- | --- | --- |
| 普通论文 | 苹果翻译 | [`main`](https://github.com/BiwayTong/paper-revision-translation-only/tree/main) |
| 普通论文 | Google 翻译 | [`google-translate`](https://github.com/BiwayTong/paper-revision-translation-only/tree/google-translate) |
| Turnitin 蓝色高亮 | 苹果翻译 | [`turnitin-highlights`](https://github.com/BiwayTong/paper-revision-translation-only/tree/turnitin-highlights) |
| Turnitin 蓝色高亮 | Google 翻译 | [`turnitin-highlights-google`](https://github.com/BiwayTong/paper-revision-translation-only/tree/turnitin-highlights-google) |

## 安装本分支

```sh
git clone --branch main --single-branch https://github.com/BiwayTong/paper-revision-translation-only.git ~/.codex/skills/apple-translate-paper-revision-translation-only
```

也可以从发布页下载 `apple-translate-paper-revision-translation-only.zip`，将解压后的同名目录放入 Codex 的 `skills` 目录，默认位置为 `~/.codex/skills/`。[下载发布版](https://github.com/BiwayTong/paper-revision-translation-only/releases/latest)

在新的 Codex 会话中附上文件并输入：

> 用 $apple-translate-paper-revision-translation-only 按指定范围跑完三轮，保留我的措辞，给我定稿和过程稿。

自动翻译使用 macOS 上分别配置为英译中与中译英的两个苹果翻译快捷指令。普通文本工具使用 Python，Word 处理另需 lxml。 [操作与恢复](references/workflow.md)
