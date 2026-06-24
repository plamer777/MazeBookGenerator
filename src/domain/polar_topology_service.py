"""Сервис для работы с полярной топологией лабиринта."""

from __future__ import annotations

import math
from collections import deque
from typing import Dict, Iterator, Sequence, Set

Cell = tuple[int, int]
Connections = Dict[Cell, Set[Cell]]


class PolarTopologyService:
    """Отвечает за топологию полярного лабиринта с динамическим разбиением (subdivision)."""

    def __init__(self, cells_per_ring: Sequence[int]):
        if not cells_per_ring:
            raise ValueError("Список колец не может быть пустым")
        if cells_per_ring[0] != 1:
            raise ValueError("Центральное кольцо должно содержать одну ячейку")

        # Строгая валидация симметрии: следующее кольцо равно предыдущему или ровно в 2 раза больше
        for i in range(2, len(cells_per_ring)):
            prev = cells_per_ring[i-1]
            curr = cells_per_ring[i]
            if curr != prev and curr != prev * 2:
                raise ValueError(f"Ошибка разбиения сетки: {prev} -> {curr}. Разрешено только 1:1 или 1:2.")

        self.cells_per_ring: list[int] = list(cells_per_ring)
        self.num_rings: int = len(self.cells_per_ring)
        self._sector_bounds: list[list[tuple[float, float]]] = [
            [self._compute_bounds(ring, sector) for sector in range(count)]
            for ring, count in enumerate(self.cells_per_ring)
        ]

    def iter_cells(self) -> Iterator[Cell]:
        for ring, count in enumerate(self.cells_per_ring):
            for sector in range(count):
                yield (ring, sector)

    def total_cells(self) -> int:
        return sum(self.cells_per_ring)

    def get_sector_bounds(self, ring: int, sector: int) -> tuple[float, float]:
        self._validate_cell(ring, sector)
        return self._sector_bounds[ring][sector]

    def get_sector_center_angle(self, ring: int, sector: int) -> float:
        start, end = self.get_sector_bounds(ring, sector)
        return (start + end) / 2

    def get_inner_neighbor(self, ring: int, sector: int) -> Cell | None:
        if ring == 0:
            return None
        if ring == 1:
            return (0, 0)

        inner_count = self.cells_per_ring[ring - 1]
        current_count = self.cells_per_ring[ring]

        if current_count == inner_count:
            return (ring - 1, sector)
        return (ring - 1, sector // 2)

    def get_outer_neighbors(self, ring: int, sector: int) -> list[Cell]:
        if ring == self.num_rings - 1:
            return []
        if ring == 0:
            return [(1, i) for i in range(self.cells_per_ring[1])]

        outer_count = self.cells_per_ring[ring + 1]
        current_count = self.cells_per_ring[ring]

        if outer_count == current_count:
            return [(ring + 1, sector)]
        return [(ring + 1, sector * 2), (ring + 1, sector * 2 + 1)]

    def get_clockwise_neighbor(self, ring: int, sector: int) -> Cell:
        if ring == 0: return (0, 0)
        count = self.cells_per_ring[ring]
        return (ring, (sector + 1) % count)

    def get_counter_clockwise_neighbor(self, ring: int, sector: int) -> Cell:
        if ring == 0: return (0, 0)
        count = self.cells_per_ring[ring]
        return (ring, (sector - 1) % count)

    def iter_neighbor_candidates(self, ring: int, sector: int) -> list[Cell]:
        neighbors: list[Cell] = []
        inner = self.get_inner_neighbor(ring, sector)
        if inner is not None:
            neighbors.append(inner)
        neighbors.extend(self.get_outer_neighbors(ring, sector))

        if ring > 0:
            neighbors.append(self.get_clockwise_neighbor(ring, sector))
            neighbors.append(self.get_counter_clockwise_neighbor(ring, sector))
        return neighbors

    def inner_neighbor_interval(self, ring: int, sector: int) -> tuple[Cell, float, float] | None:
        inner = self.get_inner_neighbor(ring, sector)
        if inner is None:
            return None
        start, end = self.get_sector_bounds(ring, sector)
        return inner, start, end

    def outer_neighbor_intervals(self, ring: int, sector: int) -> list[tuple[Cell, float, float]]:
        intervals = []
        for neighbor in self.get_outer_neighbors(ring, sector):
            n_start, n_end = self.get_sector_bounds(*neighbor)
            intervals.append((neighbor, n_start, n_end))
        return intervals

    def radial_angle(self, inner_cell: Cell, outer_cell: Cell) -> float:
        inner_start, inner_end = self.get_sector_bounds(*inner_cell)
        outer_start, outer_end = self.get_sector_bounds(*outer_cell)
        overlap_start = max(inner_start, outer_start)
        overlap_end = min(inner_end, outer_end)
        if overlap_start >= overlap_end:
            return (inner_start + inner_end) / 2
        return (overlap_start + overlap_end) / 2

    def validate_connections(self, connections: Connections) -> None:
        all_cells = list(self.iter_cells())
        for cell in all_cells:
            connections.setdefault(cell, set())

        for cell, neighbors in connections.items():
            for neighbor in neighbors:
                if cell not in connections.get(neighbor, set()):
                    raise ValueError(f"Нарушена симметрия между {cell} и {neighbor}")

        start = (0, 0)
        visited = {start}
        queue = deque([start])

        while queue:
            current = queue.popleft()
            for neighbor in connections[current]:
                if neighbor not in visited:
                    visited.add(neighbor)
                    queue.append(neighbor)

        if len(visited) != len(all_cells):
            raise ValueError("Граф содержит изолированные области")

    def _compute_bounds(self, ring: int, sector: int) -> tuple[float, float]:
        if ring == 0:
            return 0.0, 2 * math.pi
        count = self.cells_per_ring[ring]
        start = (sector / count) * 2 * math.pi
        end = ((sector + 1) / count) * 2 * math.pi
        return start, end

    def _validate_cell(self, ring: int, sector: int) -> None:
        if not (0 <= ring < self.num_rings):
            raise ValueError(f"Некорректное кольцо: {ring}")
        if ring > 0 and not (0 <= sector < self.cells_per_ring[ring]):
            raise ValueError(f"Некорректный сектор {sector} для кольца {ring}")