# VocoType GUI Modernization Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** 将 `app/gui.py` 改造成现代卡片风界面，并保持录音逻辑不变，仅显示 `就绪` / `录音中` 两态。

**Architecture:** 保持单文件 `tkinter` 架构，在 `VocotypeTkApp` 中重构 `_build_ui` 与 `_draw_record_button` 的表现层结构，并简化 `_refresh_recording_state`。新增少量纯函数用于状态文案映射与视觉状态映射，保证可以被单元测试覆盖而不依赖 GUI 运行时。

**Tech Stack:** Python 3, tkinter/ttk, unittest（标准库）

---

### Task 1: 提取可测试的状态映射函数

**Files:**
- Modify: `app/gui.py`
- Create: `tests/test_gui_status.py`
- Test: `tests/test_gui_status.py`

- [ ] **Step 1: Write the failing test**

```python
import unittest

from app.gui import derive_status_text, derive_hint_text


class TestGuiStatus(unittest.TestCase):
    def test_status_text_when_running(self):
        self.assertEqual(derive_status_text(True), "录音中")

    def test_status_text_when_idle(self):
        self.assertEqual(derive_status_text(False), "就绪")

    def test_hint_text_when_running(self):
        self.assertEqual(derive_hint_text(True), "点击停止录音")

    def test_hint_text_when_idle(self):
        self.assertEqual(derive_hint_text(False), "点击开始录音")
```

- [ ] **Step 2: Run test to verify it fails**

Run: `python -m unittest tests/test_gui_status.py -v`  
Expected: `ImportError` or `AttributeError` because `derive_status_text` / `derive_hint_text` do not exist yet.

- [ ] **Step 3: Write minimal implementation**

```python
def derive_status_text(is_recording: bool) -> str:
    return "录音中" if is_recording else "就绪"


def derive_hint_text(is_recording: bool) -> str:
    return "点击停止录音" if is_recording else "点击开始录音"
```

- [ ] **Step 4: Run test to verify it passes**

Run: `python -m unittest tests/test_gui_status.py -v`  
Expected: all tests PASS.

- [ ] **Step 5: Commit**

```bash
git add app/gui.py tests/test_gui_status.py
git commit -m "test: add gui status text mapping coverage"
```

### Task 2: 重构主布局为现代卡片结构

**Files:**
- Modify: `app/gui.py`
- Test: `tests/test_gui_status.py`

- [ ] **Step 1: Write the failing UI structure assertions**

```python
import inspect
from app.gui import VocotypeTkApp

def test_build_ui_contains_card_container_names():
    src = inspect.getsource(VocotypeTkApp._build_ui)
    assert "status_card" in src
    assert "content_card" in src
```

- [ ] **Step 2: Run test to verify it fails**

Run: `python -m unittest tests/test_gui_status.py -v`  
Expected: FAIL because `_build_ui` has no `status_card` / `content_card` markers.

- [ ] **Step 3: Write minimal implementation**

```python
# in _build_ui()
main = ttk.Frame(self, padding=16, style="App.TFrame")
status_card = ttk.Frame(main, style="Card.TFrame", padding=(12, 10))
content_card = ttk.Frame(main, style="Card.TFrame", padding=(18, 14))
```

并补充：

```python
# in _setup_styles()
style.configure("App.TFrame", background="#f3f5fb")
style.configure("Card.TFrame", background="#ffffff", relief="flat")
style.configure("StatusTitle.TLabel", background="#ffffff", foreground="#22314f")
style.configure("Muted.TLabel", background="#ffffff", foreground="#7d8caf")
```

- [ ] **Step 4: Run tests and smoke-check UI**

Run:  
- `python -m unittest tests/test_gui_status.py -v`  
- `python main.py`  
Expected: tests PASS; UI 出现顶部状态条、中央大按钮、底部退出，卡片风生效。

- [ ] **Step 5: Commit**

```bash
git add app/gui.py tests/test_gui_status.py
git commit -m "feat: refactor gui into modern card layout"
```

### Task 3: 简化状态刷新逻辑为两态并联动视觉

**Files:**
- Modify: `app/gui.py`
- Modify: `tests/test_gui_status.py`
- Test: `tests/test_gui_status.py`

- [ ] **Step 1: Add failing tests for dot color mapping**

```python
from app.gui import derive_indicator_color

def test_indicator_color_running():
    assert derive_indicator_color(True) == "#e45757"

def test_indicator_color_idle():
    assert derive_indicator_color(False) == "#8fa2d7"
```

- [ ] **Step 2: Run tests to verify failure**

Run: `python -m unittest tests/test_gui_status.py -v`  
Expected: FAIL due to missing `derive_indicator_color`.

- [ ] **Step 3: Implement two-state refresh behavior**

```python
def derive_indicator_color(is_recording: bool) -> str:
    return "#e45757" if is_recording else "#8fa2d7"

# in _refresh_recording_state()
is_recording = bool(self._rt.worker.is_running)
self._status_var.set(derive_status_text(is_recording))
self._record_hint_var.set(derive_hint_text(is_recording))
self._indicator_canvas.itemconfigure(self._indicator_dot, fill=derive_indicator_color(is_recording))
```

并删除 `pending` 队列文案路径。

- [ ] **Step 4: Run tests and manual verification**

Run:  
- `python -m unittest tests/test_gui_status.py -v`  
- `python main.py`  
Expected: tests PASS; 状态只在 `就绪` / `录音中` 间切换；无 `处理中（N 段）` 文案。

- [ ] **Step 5: Commit**

```bash
git add app/gui.py tests/test_gui_status.py
git commit -m "feat: simplify gui status to idle and recording states"
```

### Task 4: 回归检查与收尾

**Files:**
- Modify: `app/gui.py` (only if fixes needed)
- Test: `tests/test_gui_status.py`
- Docs: `docs/superpowers/specs/2026-04-23-gui-modernization-design.md`

- [ ] **Step 1: Validate close/error behavior manually**

Run: `python main.py`  
Expected:
- 录音中点击关闭 -> 确认弹窗存在
- 切换录音异常 -> 错误弹窗依然可见

- [ ] **Step 2: Full test rerun**

Run: `python -m unittest tests/test_gui_status.py -v`  
Expected: PASS.

- [ ] **Step 3: Final code quality check**

Run: `python -m py_compile app/gui.py`  
Expected: no syntax error.

- [ ] **Step 4: Commit**

```bash
git add app/gui.py tests/test_gui_status.py
git commit -m "chore: finalize gui modernization polish and verification"
```
