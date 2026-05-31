"""Навчальні матеріали: купа «з нуля» та покрокова візуалізація.

`heapq` — не магія. Тут купа реалізована вручну (лише sift-up / sift-down),
щоб показати, *чому* push і pop коштують O(log n). Дає той самий порядок, що й
`heapq` (звірено у `tests/`). Функції `*_steps` і `draw_heap`
використовуються для покрокових діаграм у документації (Розділ 04).
"""
from __future__ import annotations

import math


class MyHeap:
    """Власна купа на звичайному списку — лише sift-up і sift-down."""

    def __init__(self):
        self.heap = []

    def push(self, value):
        self.heap.append(value)
        i = len(self.heap) - 1                            # 1) у кінець
        while i > 0:                                      # 2) sift-up
            parent = (i - 1) // 2
            if self.heap[i] < self.heap[parent]:
                self.heap[i], self.heap[parent] = self.heap[parent], self.heap[i]
                i = parent
            else:
                break

    def pop(self):
        top = self.heap[0]
        last = self.heap.pop()                            # 1) забрати корінь
        if self.heap:
            self.heap[0] = last
            i = 0
            n = len(self.heap)                            # 2) останній → корінь, sift-down
            while True:
                left, right = 2 * i + 1, 2 * i + 2
                smallest = i
                if left < n and self.heap[left] < self.heap[smallest]:
                    smallest = left
                if right < n and self.heap[right] < self.heap[smallest]:
                    smallest = right
                if smallest == i:
                    break
                self.heap[i], self.heap[smallest] = self.heap[smallest], self.heap[i]
                i = smallest
        return top


def sift_up_steps(arr, value):
    """Записує кадри підняття нового елемента `value` (для анімації PUSH)."""
    nodes = list(arr)
    nodes.append(value)
    i = len(nodes) - 1
    steps: list[tuple] = [(list(nodes), i, None)]
    while i > 0:
        parent = (i - 1) // 2
        if nodes[i][0] < nodes[parent][0]:
            steps.append((list(nodes), i, (i, parent)))      # перед обміном
            nodes[i], nodes[parent] = nodes[parent], nodes[i]
            i = parent
            steps.append((list(nodes), i, None))             # після обміну
        else:
            break
    return steps


def sift_down_steps(arr):
    """Записує кадри занурення кореня (для анімації POP)."""
    nodes = list(arr)
    nodes[0] = nodes[-1]
    nodes.pop()                               # останній лист → у корінь
    steps: list[tuple] = [(list(nodes), 0, None)]
    i = 0
    n = len(nodes)
    while True:
        left, right = 2 * i + 1, 2 * i + 2
        smallest = i
        if left < n and nodes[left][0] < nodes[smallest][0]:
            smallest = left
        if right < n and nodes[right][0] < nodes[smallest][0]:
            smallest = right
        if smallest == i:
            break
        steps.append((list(nodes), i, (i, smallest)))
        nodes[i], nodes[smallest] = nodes[smallest], nodes[i]
        i = smallest
        steps.append((list(nodes), i, None))
    return steps


def draw_heap(ax, arr, title, highlight=None, swap=None, sev_colors=None):
    """Малює купу (масив пар (severity, id)) як бінарне дерево на осі matplotlib."""
    import matplotlib.pyplot as plt

    if sev_colors is None:
        from .model import SEV_COLORS as sev_colors
    n = len(arr)
    pos = {}
    for i in range(n):
        depth = int(math.floor(math.log2(i + 1)))
        idx = i - (2 ** depth - 1)
        pos[i] = ((idx + 0.5) / (2 ** depth), -depth)
    for i in range(n):                                   # ребра
        for child in (2 * i + 1, 2 * i + 2):
            if child < n:
                ax.plot([pos[i][0], pos[child][0]], [pos[i][1], pos[child][1]], "k-", lw=1, zorder=1)
    for i in range(n):                                   # вузли
        sev, pid = arr[i]
        node_x, node_y = pos[i]
        edge_color, line_width = "black", 1.5
        if highlight and i in highlight:
            edge_color, line_width = "blue", 3
        if swap and i in swap:
            edge_color, line_width = "red", 3
        ax.add_patch(plt.Circle((node_x, node_y), 0.07, color=sev_colors[sev],
                                ec=edge_color, lw=line_width, zorder=2))
        ax.text(node_x, node_y, f"{sev}", ha="center", va="center", fontsize=11, fontweight="bold", zorder=3)
        ax.text(node_x, node_y - 0.13, pid, ha="center", va="center", fontsize=7, color="gray", zorder=3)
        ax.text(node_x + 0.05, node_y + 0.09, f"[{i}]", ha="center", va="center", fontsize=7, color="#888", zorder=3)
    ax.set_xlim(-0.1, 1.1)
    ax.set_ylim(-3.2, 0.5)
    ax.axis("off")
    ax.set_title(title, fontweight="bold", fontsize=11)
