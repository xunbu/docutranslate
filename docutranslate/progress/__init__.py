# SPDX-FileCopyrightText: 2025 QinHan
# SPDX-License-Identifier: MPL-2.0
"""进度跟踪模块"""
import threading
from dataclasses import dataclass, field
from logging import Logger
from typing import Callable, Optional


@dataclass
class ProgressStep:
    """进度步骤"""
    name: str
    weight: int = 1  # 权重，默认1


class ProgressTracker:
    """
    进度跟踪器

    支持:
    - 定义多个步骤及其权重
    - 实时更新进度
    - 集成logger记录日志
    - 线程安全
    """

    def __init__(
        self,
        logger: Optional[Logger] = None,
        total_steps: int = 100,
        callback: Optional[Callable[[int, str], None]] = None
    ):
        """
        初始化进度跟踪器

        Args:
            logger: 日志记录器，用于记录进度日志
            total_steps: 总步数 (默认100，对应百分比)
            callback: 进度更新回调函数，签名为 (percent: int, message: str) -> None
        """
        self.logger = logger
        self.total_steps = total_steps
        self.callback = callback
        self._current_step = 0
        self._current_percent = 0
        self._message = ""
        self._lock = threading.Lock()
        self._steps: list[ProgressStep] = []
        self._step_weights: list[int] = []
        self._total_weight = 0
        self._completed_weight = 0

    def set_steps(self, steps: list[str | ProgressStep]) -> "ProgressTracker":
        """
        设置进度步骤

        Args:
            steps: 步骤名称列表，或 ProgressStep 列表

        Returns:
            self，便于链式调用
        """
        self._steps = [
            s if isinstance(s, ProgressStep) else ProgressStep(name=s)
            for s in steps
        ]
        self._step_weights = [s.weight for s in self._steps]
        self._total_weight = sum(self._step_weights)
        return self

    def update(
        self,
        step: Optional[int] = None,
        message: str = "",
        percent: Optional[int] = None
    ) -> "ProgressTracker":
        """
        更新进度

        Args:
            step: 步骤索引 (0-based)，设置后自动计算百分比
            message: 进度消息
            percent: 直接指定百分比 (0-100)，优先级高于 step

        Returns:
            self，便于链式调用
        """
        with self._lock:
            if percent is not None:
                self._current_percent = max(0, min(100, percent))
            elif step is not None:
                self._current_step = step
                if self._total_weight > 0:
                    # 根据权重计算百分比
                    self._completed_weight = sum(self._step_weights[:step + 1])
                    self._current_percent = int((self._completed_weight / self._total_weight) * 100)
                else:
                    self._current_percent = int(((step + 1) / len(self._steps)) * 100) if self._steps else 0
            else:
                # 递增一步
                self._current_step += 1
                if self._steps and self._current_step < len(self._steps):
                    self._current_percent = int(((self._current_step) / len(self._steps)) * 100)

            self._message = message

            # 记录日志
            if self.logger and message:
                self.logger.info(f"[{self._current_percent}%] {message}")

            # 调用回调
            if self.callback:
                self.callback(self._current_percent, message)

        return self

    @property
    def percent(self) -> int:
        """获取当前进度百分比"""
        return self._current_percent

    @property
    def message(self) -> str:
        """获取当前进度消息"""
        return self._message

    @property
    def current_step(self) -> int:
        """获取当前步骤索引"""
        return self._current_step

    def get_status(self) -> dict:
        """获取进度状态"""
        return {
            "percent": self._current_percent,
            "message": self._message,
            "current_step": self._current_step,
            "total_steps": len(self._steps),
        }

    def reset(self) -> "ProgressTracker":
        """重置进度"""
        with self._lock:
            self._current_step = 0
            self._current_percent = 0
            self._message = ""
            self._completed_weight = 0
        return self


class NullProgressTracker(ProgressTracker):
    """空进度跟踪器，用于不需要进度跟踪的场景"""

    def __init__(self):
        super().__init__(logger=None)

    def update(self, step=None, message="", percent=None):
        return self  # 不做任何操作


# 全局空进度跟踪器
null_progress = NullProgressTracker()
