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

### 使用 Google Cloud 自动翻译

使用已启用 Cloud Translation API 的 Google Cloud 项目。可以在运行进程中设置环境变量 `GOOGLE_TRANSLATE_API_KEY`，或为 Python 安装 `google-auth[requests]` 并配置应用默认凭据（ADC）。使用个人 ADC 时，需要具备相应权限的配额项目，可通过 `GOOGLE_CLOUD_QUOTA_PROJECT` 指定。密钥留在本机的环境变量或密钥管理器中。实际提交给 Google 的是选定段落，费用和配额以所用项目为准。[身份验证](https://cloud.google.com/translate/docs/authentication) · [官方接口](https://cloud.google.com/translate/docs/reference/rest/v2/translate) · [计费](https://cloud.google.com/translate/pricing)

```sh
python scripts/google_rounds.py job 1 zh
# 阅读 r1-zh-raw.json，将中文建议稿或作者修改稿写入 job/r1-zh-edit.json
python scripts/google_rounds.py job 1 en
# 阅读 r1-en-raw.json，将核对后的英文写入 job/r1-en-edit.json
```

第二轮和第三轮分别把轮次改为 `2` 和 `3`。英译中的输入是第一轮的基准稿或上一轮英文调整稿，中译英的输入始终是本轮中文调整稿。JSON 调整稿沿用基准稿的全部编号。对于 Google 原样返回的空格、标点或字符实体，保留原始输出，在调整稿中按语境处理。

每个成功段落独立记录翻译渠道、语言方向、输入与译文指纹。临时网络错误或限流缓解后重跑当前步骤，程序会从缺失的段落继续。出现 `SERVICE_DISABLED` 时，检查所用项目是否已启用 Cloud Translation API，或继续使用网页方式。遇到长度上限应按句界分段，记录各段位置及原始译文，再按原顺序回填。

### 使用 Google 翻译网页

没有 Cloud 凭据也可完成三轮。每次导出当前步骤的待译表，在 Google 翻译网页设置表内指定的英中方向，逐段提交 `source`，把显示的完整译文原样填入对应的 `translation`。保留编号、轮次、语言和源文。编辑者有网页访问权限时直接操作，否则请用户返回填好的表。每次都要实际取得本轮译文。[打开 Google 翻译](https://translate.google.com/)

```sh
python scripts/google_rounds.py job 1 zh --export-web r1-zh-web.json
# 填入网页译文后导入
python scripts/google_rounds.py job 1 zh --import-web r1-zh-web.json
```

中译英将 `zh` 换为 `en`，各轮各方向使用独立文件。部分导入会保存已填段落并列出缺少的编号。导入时程序核对源文、轮次和方向。归档中的 `provider` 用 `google-translate-web` 标记网页译文，用 `google-cloud-translation-v2` 标记 API 返回值。若两种渠道均不可用，交付当前待译表及进度。

### 第三轮英文编辑

第三轮英文回译原样存入 `job/r3-en-raw.json`，直接对照英文基准稿，仅修复确认的偏移，将结果另存为 `job/r3-en-edit.json`。对照基准稿时，若回译把 “The estimate may rise by 4–6% [7].” 改成 “The estimate will rise by 4–6% [7].”，只将 `will` 改回 `may`。若原句仅换了一种同义说法，最终稿采用作者原句。未发现具体问题时，编辑稿直接沿用回译，在 `job/review.md` 简记复核结果。

## 成稿

```sh
python scripts/manuscript.py merge paper.docx job revised.docx
python scripts/package_process.py job process.zip
```

先将对照检查稿另存为 `job/check.json`，再将最小校对后的文本写入 `job/final.json`。合并时输入原始文件及原工作目录，选择新文件名；TXT 的合并用法相同。工具检查底稿、编号和每处原文，Word 只写入选定文字并核验包内其余部件。对混排段落核对样式边界、链接和引文显示是否完整。

把修改原因、中文稿来源、待核实项、最终词数及统计口径写入 `job/review.md`。以拼回后的整篇正文或用户给出的完整摘录为计数对象。打包命令复核六组翻译记录，生成三轮合并阅读稿及按编号的基准稿、第三轮中文稿和最终英文对照。
