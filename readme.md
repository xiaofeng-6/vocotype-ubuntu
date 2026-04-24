# VocoType - 精准的离线语音输入法

<h2 align="center">您的声音，绝不离开电脑</h2>

**VocoType** 是一款专为注重隐私和效率的专业人士打造的、**完全免费**的桌面端语音输入法。所有识别均在本地完成，无惧断网，不上传任何数据。

## 重要说明（请先看）

本仓库是我个人维护的 **Ubuntu 定制版本**（与官方版本不同），目标是做成 **专门为 Ubuntu 开发的语音输入工具**（含 GUI 与 `.deb` 打包）。

- **官方版本**：目前 **不支持 Ubuntu**，仅支持 **Windows** 与 **macOS**
- **本仓库**：面向 Ubuntu 使用与开发（CLI + 轻量桌面 GUI）

---

### **➡️ 想获得最佳体验？请立即下载免费桌面版！**

开箱即用，功能更完整，无需任何技术背景。

**[立即访问官网，下载免费、完整的 VocoType 桌面版](https://vocotype.com)**

## 功能简介

VocoType 是一款智能语音输入工具，通过快捷键即可将语音实时转换为文字并自动输入到当前应用。支持MCP语音转文字、 AI 优化文本、自定义替换词典等功能，让语音输入更高效、更准确。

### 📹 演示视频

<video controls width="100%">
  <source src="https://s1.bib0.com/leilei/i/2025/11/04/5yba.mp4" type="video/mp4">
  您的浏览器不支持视频播放。
</video>


## 下载

### 官方版本（不支持 Ubuntu）

| OS | Download |
|---|---|
| **Windows** | [![Setup](https://img.shields.io/badge/Setup-x64-blue)](https://github.com/233stone/vocotype-cli/releases/download/v1.5.4/VocoType_1.5.4_x64-setup.exe) |
| **macOS** | [![DMG](https://img.shields.io/badge/DMG-Apple%20Silicon-black)](https://github.com/233stone/vocotype-cli/releases/download/v1.5.4/VocoType_1.5.4_Universal.dmg) [![DMG](https://img.shields.io/badge/DMG-Intel-black)](https://github.com/233stone/vocotype-cli/releases/download/v1.5.4/VocoType_1.5.4_Universal.dmg) |

### Ubuntu（本仓库个人版本）

本仓库提供 Ubuntu 构建与安装方式，见下文 **“3.1 Ubuntu 桌面应用（.deb）”**。
---



## 🤔 VocoType 为何与众不同？

| 特性           |    ✅ **VocoType**     |  传统云端输入法   |  操作系统自带   |
| :------------- | :--------------------: | :---------------: | :-------------: |
| **隐私安全**   | **本地离线，绝不上传** | ❌ 数据需上传云端 | ⚠️ 隐私政策复杂 |
| **网络依赖**   |    **完全无需联网**    |  ❌ 必须联网使用  |  ❌ 强依赖网络  |
| **响应速度**   |      **0.1 秒级**      |  慢，受网速影响   | 慢，受网速影响  |
| **定制化能力** |  **强大的自定义词表**  |      弱或无       |    基本没有     |

## ✅ 核心功能

- **完整的图形用户界面**：开箱即用，所有操作清晰直观。
- **系统级全局输入**：在任何软件、任何文本框内都能直接语音输入。
- **自定义词典**：支持添加 20 个常用术语、人名，提升识别准确率。
- **100% 离线运行**：绝对的隐私和数据安全。
- **旗舰级识别引擎**：精准识别中英混合内容。
- **AI 智能优化**：支持选择多种 AI 模型，通过可定制的 Prompt 模板自动修正语音转录中的错别字、同音字和自我修正，智能识别口语中的修正指令（如"不对"、"改成"等），让输出文本更准确流畅。

_(对于有更高需求的专业用户，应用内提供了升级到 Pro 版的选项，以解锁无限词典等高级功能。)_

## 🎯 适用各类专业场景

无论是文字工作者、律师、学者、游戏玩家，还是日常办公，VocoType 都能成为您值得信赖的效率伙伴。

| 用户                | 场景                                                                                           |
| :------------------ | :--------------------------------------------------------------------------------------------- |
| **作家与创作者**    | 撰写文章、小说，整理会议纪要，让思绪通过语音即时转化为文字，心无旁骛，专注于创作本身。         |
| **法律 & 医疗人士** | 处理高度敏感的客户信息或病历时，100%离线确保数据安全。自定义词表更能轻松驾驭行业术语。         |
| **学生与学者**      | 快速记录课堂笔记、整理访谈录音、撰写学术论文。告别繁琐的打字，将更多精力投入到思考与研究之中。 |
| **开发者 & 程序员** | 无论是与 AI 结对编程，还是撰写技术文档，都能精准识别 `function`、`Kubernetes pod` 等专业术语。 |
| **游戏玩家**        | 在激烈的游戏对战中，通过语音快速打字与队友交流，无需停下操作，保持游戏节奏，提升团队协作效率。 |

## ✨ VocoType 核心引擎特性

_所有 VocoType 版本共享同一个强大的核心引擎。_

- **🛡️ 100% 离线，隐私无忧**：所有语音识别在您的电脑本地完成。
- **⚡️ 旗舰级识别引擎**：中英混合输入同样精准，告别反复修改。
- **⚙️ 高度可定制**：独创的替换词表功能，让人名、地名、行业术语一次就对。
- **💻 轻量化设计**：仅需 700MB 内存，纯 CPU 推理，无需昂贵显卡。
- **🚀 0.1 秒级响应**：感受所言即所得的畅快，让您的灵感不再因等待而中断。

---

## 🛠️ 【开发者专属】CLI 版安装指南

**请注意：** 此版本面向有一定技术背景的开发者。如果您不熟悉命令行，我们强烈建议您访问官网，下载简单易用的 **VocoType 免费桌面版**。

### 1. 环境依赖

- Python 3.12 推荐；最低 Python 3.10 也可尝试
- 推荐使用 **[uv](https://docs.astral.sh/uv/)** 管理解释器与依赖：比 Conda 更轻、启动快、项目里只要一个 **`.venv`** 目录，不污染系统 Python

### 2. 安装 uv（三选一）

```bash
# 官方单文件安装器（推荐，不依赖本机已装 Python）
curl -LsSf https://astral.sh/uv/install.sh | sh
# 装好后把 $HOME/.local/bin 加进 PATH（安装脚本会提示）
```

或 **`pipx install uv`**；或用 **`python3 -m pip install --user uv`**（不如前两种独立）。

若本机没有 3.12，可用 **uv 自带安装解释器**（Linux/macOS/Windows 均可）：

```bash
uv python install 3.12
```

### 3. 克隆、建环境、装依赖、运行

```bash
git clone https://github.com/233stone/vocotype-cli.git
cd vocotype-cli   # 或你本地的 vocotype-ubuntu 等目录

# 在仓库根目录建虚拟环境并指向 3.12
uv venv -p 3.12
source .venv/bin/activate   # Linux / macOS
# Windows:  .\.venv\Scripts\activate

# 用 uv 调用 pip 安装本仓库依赖（与 pip 一样，但更快、能锁解析）
uv pip install -r requirements.txt

# 运行（Linux 全局热键常需: sudo -E .venv/bin/python main.py，保留你当前环境变量）
python main.py

# 保存训练/数据集
python main.py --save-dataset
```

不激活 venv 时也可**显式指定解释器**：

```bash
uv venv -p 3.12
uv pip install --python .venv/bin/python -r requirements.txt
.venv/bin/python main.py
```

### 3.1 Ubuntu 桌面应用（.deb）

在仓库根目录执行 `bash packaging/ubuntu/build-deb.sh` 生成 `vocotype-ubuntu_<version>_all.deb`（版本号见 `packaging/ubuntu/VERSION`）。安装：

```bash
sudo apt install ./vocotype-ubuntu_*_all.deb
```

首次安装会在 `/opt/vocotype-ubuntu/.venv` 内执行 `pip install -r requirements.txt`，**需要联网**。安装完成后可在应用菜单启动 **VocoType**，或运行 `vocotype`。

补充说明：

- **日志目录**：安装到 `/opt` 时，日志会写入 `~/.local/state/vocotype-ubuntu/logs`（避免 `/opt` 无写权限导致桌面启动无反应）。
- **apt 本地文件权限提示**：若出现 `_apt` 无法访问 `.deb` 的提示，这是正常的沙盒提示。可将 `.deb` 复制到 `/tmp` 后再安装以避免提示：

```bash
cp ./vocotype-ubuntu_*_all.deb /tmp/
sudo apt install /tmp/vocotype-ubuntu_*_all.deb
```

- **F9 全局热键（Linux）**：优先尝试 `keyboard`，失败则自动降级为 `pynput`（在 **X11** 下通常无需 root）。若仍不可用，程序仍可启动，且可使用窗口里的按钮开始/停止录音。**Wayland** 环境对全局热键/注入常有系统级限制，建议切换到 X11 或调整实现方式。

### 4. 与 Conda 的取舍

| | uv + `.venv` | Conda |
| :--- | :--- | :--- |
| 体积 / 管理 | 极轻、按项目分目录 | 基环境较大、多环境占盘 |
| 适合 | 单项目、纯 PyPI 依赖 | 要科学计算全家桶、多语言栈 |
| 建议 | 本项目默认推荐 | 若你整台机已经深度绑在 Conda 上也可继续用 |

> **模型下载**：首次运行时，程序会自动下载约 500MB 的模型文件，请确保网络连接稳定。

## 🌐 Volcengine 火山引擎 BigASR 流式识别后端（可选）

除了默认的本地 FunASR 离线引擎，VocoType CLI 还支持接入[火山引擎豆包大模型流式语音识别](https://www.volcengine.com/docs/6561/1354869)作为云端识别后端。

### 优势

| 特性 | 本地 FunASR | Volcengine BigASR |
|:--|:--:|:--:|
| 网络要求 | 无 | 需要联网 |
| 模型下载 | ~500 MB | 无需下载 |
| 响应延迟 | 本地推理 | 云端极低延迟 |
| 识别质量 | 高 | 旗舰级大模型 |
| 数据隐私 | 完全离线 | 音频发送至火山引擎 |

### 配置步骤

1. 登录[火山引擎控制台](https://console.volcengine.com/speech/app)，创建一个语音应用，获取 **App Key** 和 **Access Key**。

2. 在项目目录创建 `config.json`：

```json
{
  "backend": "volcengine",
  "volcengine": {
    "app_key": "YOUR_APP_KEY",
    "access_key": "YOUR_ACCESS_KEY",
    "resource_id": "volc.bigasr.sauc.duration",
    "enable_punc": true,
    "enable_itn": true
  }
}
```

3. 以 `--config` 参数启动：

```bash
python main.py --config config.json
```

> **注意**：使用 Volcengine 后端时，录音数据会发送到火山引擎服务器进行识别，不再完全离线。如对隐私有严格要求，请继续使用默认的本地 FunASR 后端。

## 常见问题 (FAQ)

**Q: 我的数据安全吗？**

> A: **100%安全**。所有语音识别均在本地离线完成，您的音频数据不会上传到任何服务器。

## 📞 联系我们

- **Bug 与建议**：请优先使用 GitHub Issues。
- **关注我们获取最新动态**：[https://vocotype.com](https://vocotype.com)

## 🙏 致谢

VocoType 的诞生离不开以下优秀的开源项目：

- **[FunASR](https://github.com/modelscope/FunASR)** - 阿里巴巴达摩院开源的语音识别框架，为 VocoType 提供了强大的离线语音识别能力。
- **[QuQu](https://github.com/yan5xu/ququ)** - 优秀的开源项目，为 VocoType 提供了重要的技术参考和灵感。

感谢这些开源社区的无私贡献！
