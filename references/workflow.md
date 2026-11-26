# 操作与恢复

从技能目录运行命令。用工作区提供的 Python，Word 处理需要 lxml。两个输入示例 `paper.docx` 和 `paper.txt` 都是普通稿件。粘贴的文字可原样保存为 UTF-8 的 `paper.txt`。每篇稿件使用新的本地工作目录。

## 列出并选取

```sh
python scripts/manuscript.py list paper.docx
python scripts/manuscript.py prepare paper.docx job --blocks B003-B005,B009
```

`list` 输出段落编号、样式和文字。编辑者据此将用户给的章节名或指定段落转换为编号，不要求用户自己找编号。Word 使用有文字的正文及表格段落；TXT 按非空物理行编号，保留源文件的空行、换行符和行首行尾空白。标题没有样式时，结合标题文字、前后段和层次来选范围。对于软换行被保存成多行的纯文本，要结合连续各行原意编辑。输入本身就是待修改的纯正文时可以用：

```sh
python scripts/manuscript.py prepare paper.txt job --blocks all
```

`scope.json` 保存底稿指纹与定位，`original.json` 保存需要翻译的编号文本。B 编号定位源段落，P 编号定位翻译单元。一段中连续且同格式的简单文字合为一个单元，样式不同的文字分别保存；调整某个单元时要通读整段。超链接文字、Word 引文域等保留在原位；`[protected text]` 表示有文字不进入自动回填。逐项判断这类受保护文字是否需要处理。若被明确选中，用支持原格式的 Word 范围编辑在副本上完成并核验。文本框、页眉、脚注正文等独立部件同理。选区仅是句子或半段时，先记下两端原文，用精确范围处理，不要把整段交给自动替换。

## 每轮实际翻译

内容核查后，将英文基准稿写为 `job/baseline.json`。从此各稿件均使用相同的编号到文本映射，例如 `{"P001": "The survey covered two sites."}`。把已核实的纠正及待核实项单独记录。

在 Mac 的“快捷指令”中检查两条指令确实使用苹果“翻译文本”动作，返回文本，各自指定英文→中文或中文→英文。下例用名称“论文英译中”和“论文中译英”，可替换为用户实际配置的名称。

```sh
python scripts/apple_rounds.py job 1 zh '论文英译中'
# 阅读 r1-zh-raw.json，把逐段调整的中文写入 job/r1-zh-edit.json
python scripts/apple_rounds.py job 1 en '论文中译英'
# 阅读 r1-en-raw.json，把核对后的英文写入 job/r1-en-edit.json
```

第二、三轮使用相同命令，将轮次分别改为 `2` 和 `3`。程序读取前一轮的英文修改稿或本轮的中文调整稿，并在 `.records/` 留存来源、输入指纹与原始译文。已有记录会核对指纹；中断后重跑相同步骤即可续跑。不得以空译、原文复写或模型自行翻译充当工具译文。

若需人工操作，将待译输入按编号交给用户。仅在用户实际使用苹果翻译并提供未经编辑的结果后，按下例导入。短专名经苹果翻译后保持原样，也可按此登记。部分导入会提示尚缺编号，已有结果会保存。

```sh
python scripts/apple_rounds.py job 1 zh --import-apple user-apple-output.json
```

### 第三轮英文编辑

第三轮英文回译原样存入 `job/r3-en-raw.json`，直接对照英文基准稿，仅修复确认的偏移，将结果另存为 `job/r3-en-edit.json`。对照基准稿时，若回译把 “The estimate may rise by 4–6% [7].” 改成 “The estimate will rise by 4–6% [7].”，只将 `will` 改回 `may`。若原句仅换了一种同义说法，最终稿采用作者原句。未发现具体问题时，编辑稿直接沿用回译，在 `job/review.md` 简记复核结果。

## 成稿

```sh
python scripts/manuscript.py merge paper.docx job revised.docx
python scripts/package_process.py job process.zip
```

先将对照检查稿另存为 `job/check.json`，再将最小校对后的文本写入 `job/final.json`。合并时输入原始文件及原工作目录，选择新文件名；TXT 的合并用法相同。工具检查底稿、编号和每处原文，Word 只写入选定文字并核验包内其余部件。对混排段落核对样式边界、链接和引文显示是否完整。

把修改原因、中文稿来源、待核实项、最终词数及统计口径写入 `job/review.md`。以拼回后的整篇正文或用户给出的完整摘录为计数对象。打包命令复核六组翻译记录，生成三轮合并阅读稿及按编号的基准稿、第三轮中文稿和最终英文对照。
