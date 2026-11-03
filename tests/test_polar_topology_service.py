"""Unit-тесты для PolarTopologyService."""


import pytest

from src.domain.polar_topology_service import PolarTopologyService


class TestPolarTopologyService:
    """Проверяет логику полярной топологии лабиринта."""

    def test_initialization_valid_simple(self) -> None:
        """Инициализация с валидным простым разбиением."""
        cells_per_ring = [1, 6, 12]
        service = PolarTopologyService(cells_per_ring)

        assert service.num_rings == 3
        assert service.cells_per_ring == [1, 6, 12]

    def test_initialization_empty_raises(self) -> None:
        """Пустой список колец должен вызывать ValueError."""
        with pytest.raises(ValueError):
            PolarTopologyService([])

    def test_initialization_center_not_one_raises(self) -> None:
        """Центральное кольцо должно содержать одну ячейку."""
        with pytest.raises(ValueError):
            PolarTopologyService([2, 6, 12])

    def test_initialization_invalid_subdivision_raises(self) -> None:
        """Некорректное разбиение (не 1:1 или 1:2) должно вызывать ValueError."""
        with pytest.raises(ValueError):
            PolarTopologyService([1, 6, 9])  # 6 -> 9 не 1:1 или 1:2

    def test_iter_cells(self) -> None:
        """Итерация по ячейкам должна возвращать все ячейки."""
        cells_per_ring = [1, 4, 8]
        service = PolarTopologyService(cells_per_ring)

        cells = list(service.iter_cells())
        assert len(cells) == 13  # 1 + 4 + 8
        assert (0, 0) in cells
        assert (1, 0) in cells
        assert (1, 3) in cells
        assert (2, 0) in cells
        assert (2, 7) in cells

    def test_total_cells(self) -> None:
        """Общее количество ячеек должно быть суммой по кольцам."""
        cells_per_ring = [1, 6, 12, 24]
        service = PolarTopologyService(cells_per_ring)

        assert service.total_cells() == 43  # 1 + 6 + 12 + 24

    def test_get_sector_bounds_center(self) -> None:
        """Границы центральной ячейки должны быть 0..2π."""
        cells_per_ring = [1, 6]
        service = PolarTopologyService(cells_per_ring)

        start, end = service.get_sector_bounds(0, 0)
        assert start == 0.0
        assert end == 2 * 3.141592653589793  # 2π

    def test_get_sector_bounds_ring(self) -> None:
        """Границы ячеек в кольце должны быть равномерными."""
        cells_per_ring = [1, 4]
        service = PolarTopologyService(cells_per_ring)

        # Кольцо с 4 ячейками: каждая занимает π/2
        start0, end0 = service.get_sector_bounds(1, 0)
        start1, end1 = service.get_sector_bounds(1, 1)

        assert start0 == pytest.approx(0.0, abs=10**-5)
        assert end0 == pytest.approx(1.5708, abs=10**-4)  # π/2
        assert start1 == pytest.approx(1.5708, abs=10**-4)  # π/2
        assert end1 == pytest.approx(3.1416, abs=10**-4)  # π

    def test_get_sector_center_angle(self) -> None:
        """Центральный угол сектора должен быть посередине границ."""
        cells_per_ring = [1, 4]
        service = PolarTopologyService(cells_per_ring)

        center = service.get_sector_center_angle(1, 0)
        assert center == pytest.approx(0.7854, abs=10**-4)  # π/4

    def test_get_inner_neighbor_center(self) -> None:
        """Внутренний сосед для центральной ячейки должен быть None."""
        cells_per_ring = [1, 6]
        service = PolarTopologyService(cells_per_ring)

        assert service.get_inner_neighbor(0, 0) is None

    def test_get_inner_neighbor_ring_1(self) -> None:
        """Внутренний сосед для первого кольца должен быть центр."""
        cells_per_ring = [1, 6]
        service = PolarTopologyService(cells_per_ring)

        assert service.get_inner_neighbor(1, 0) == (0, 0)
        assert service.get_inner_neighbor(1, 3) == (0, 0)

    def test_get_inner_neighbor_same_count(self) -> None:
        """Внутренний сосед при одинаковом количестве ячеек."""
        cells_per_ring = [1, 6, 6]
        service = PolarTopologyService(cells_per_ring)

        assert service.get_inner_neighbor(2, 0) == (1, 0)
        assert service.get_inner_neighbor(2, 3) == (1, 3)

    def test_get_inner_neighbor_double_count(self) -> None:
        """Внутренний сосед при удвоении количества ячеек."""
        cells_per_ring = [1, 6, 12]
        service = PolarTopologyService(cells_per_ring)

        assert service.get_inner_neighbor(2, 0) == (1, 0)  # 0 // 2 = 0
        assert service.get_inner_neighbor(2, 3) == (1, 1)  # 3 // 2 = 1
        assert service.get_inner_neighbor(2, 7) == (1, 3)  # 7 // 2 = 3

    def test_get_outer_neighbors_last_ring(self) -> None:
        """Внешние соседи для последнего кольца должны быть пустыми."""
        cells_per_ring = [1, 6]
        service = PolarTopologyService(cells_per_ring)

        assert service.get_outer_neighbors(1, 0) == []

    def test_get_outer_neighbors_center(self) -> None:
        """Внешние соседи для центра должны быть все ячейки первого кольца."""
        cells_per_ring = [1, 4]
        service = PolarTopologyService(cells_per_ring)

        neighbors = service.get_outer_neighbors(0, 0)
        assert len(neighbors) == 4
        assert (1, 0) in neighbors
        assert (1, 1) in neighbors
        assert (1, 2) in neighbors
        assert (1, 3) in neighbors

    def test_get_outer_neighbors_same_count(self) -> None:
        """Внешние соседи при одинаковом количестве ячеек."""
        cells_per_ring = [1, 6, 6]
        service = PolarTopologyService(cells_per_ring)

        neighbors = service.get_outer_neighbors(1, 0)
        assert len(neighbors) == 1
        assert neighbors[0] == (2, 0)

    def test_get_outer_neighbors_double_count(self) -> None:
        """Внешние соседи при удвоении количества ячеек."""
        cells_per_ring = [1, 6, 12]
        service = PolarTopologyService(cells_per_ring)

        neighbors = service.get_outer_neighbors(1, 0)
        assert len(neighbors) == 2
        assert (2, 0) in neighbors  # 0 * 2 = 0
        assert (2, 1) in neighbors  # 0 * 2 + 1 = 1

    def test_get_clockwise_neighbor(self) -> None:
        """Сосед по часовой стрелке."""
        cells_per_ring = [1, 6]
        service = PolarTopologyService(cells_per_ring)

        assert service.get_clockwise_neighbor(0, 0) == (0, 0)
        assert service.get_clockwise_neighbor(1, 0) == (1, 1)
        assert service.get_clockwise_neighbor(1, 5) == (1, 0)

    def test_get_counter_clockwise_neighbor(self) -> None:
        """Сосед против часовой стрелки."""
        cells_per_ring = [1, 6]
        service = PolarTopologyService(cells_per_ring)

        assert service.get_counter_clockwise_neighbor(0, 0) == (0, 0)
        assert service.get_counter_clockwise_neighbor(1, 0) == (1, 5)
        assert service.get_counter_clockwise_neighbor(1, 5) == (1, 4)

    def test_iter_neighbor_candidates_center(self) -> None:
        """Кандидаты-соседи для центра."""
        cells_per_ring = [1, 4]
        service = PolarTopologyService(cells_per_ring)

        candidates = service.iter_neighbor_candidates(0, 0)
        assert len(candidates) == 4  # только внешние соседи
        assert (1, 0) in candidates

    def test_iter_neighbor_candidates_ring(self) -> None:
        """Кандидаты-соседи для ячейки в кольце."""
        cells_per_ring = [1, 6, 12]
        service = PolarTopologyService(cells_per_ring)

        candidates = service.iter_neighbor_candidates(1, 0)
        # Внутренний (центр), внешние (2), угловые (2)
        assert len(candidates) >= 3

    def test_inner_neighbor_interval(self) -> None:
        """Интервал внутреннего соседа."""
        cells_per_ring = [1, 6]
        service = PolarTopologyService(cells_per_ring)

        result = service.inner_neighbor_interval(1, 0)
        assert result is not None
        neighbor, start, end = result
        assert neighbor == (0, 0)
        assert start == 0.0
        assert end == pytest.approx(1.0472, abs=10**-4)  # 2π/6

    def test_inner_neighbor_interval_center(self) -> None:
        """Интервал внутреннего соседа для центра должен быть None."""
        cells_per_ring = [1, 6]
        service = PolarTopologyService(cells_per_ring)

        assert service.inner_neighbor_interval(0, 0) is None

    def test_outer_neighbor_intervals(self) -> None:
        """Интервалы внешних соседей."""
        cells_per_ring = [1, 6, 12]
        service = PolarTopologyService(cells_per_ring)

        intervals = service.outer_neighbor_intervals(1, 0)
        assert len(intervals) == 2

    def test_outer_neighbor_intervals_last_ring(self) -> None:
        """Интервалы внешних соседей для последнего кольца должны быть пустыми."""
        cells_per_ring = [1, 6]
        service = PolarTopologyService(cells_per_ring)

        intervals = service.outer_neighbor_intervals(1, 0)
        assert len(intervals) == 0

    def test_radial_angle(self) -> None:
        """Радиальный угол для соседей."""
        cells_per_ring = [1, 6, 12]
        service = PolarTopologyService(cells_per_ring)

        inner = (1, 0)
        outer = (2, 0)
        angle = service.radial_angle(inner, outer)
        assert angle > 0.0
        assert angle < 2 * 3.141592653589793

    def test_validate_connections_empty_raises(self) -> None:
        """Пустые соединения должны вызывать ошибку изолированных областей."""
        cells_per_ring = [1, 4]
        service = PolarTopologyService(cells_per_ring)

        connections = {}
        with pytest.raises(ValueError):
            service.validate_connections(connections)

    def test_validate_connections_symmetry(self) -> None:
        """Валидация должна проверять симметрию соединений."""
        cells_per_ring = [1, 4]
        service = PolarTopologyService(cells_per_ring)

        # Связный граф с симметричными соединениями
        connections = {
            (0, 0): {(1, 0)},
            (1, 0): {(0, 0), (1, 1)},
            (1, 1): {(1, 0), (1, 2)},
            (1, 2): {(1, 1), (1, 3)},
            (1, 3): {(1, 2)},
        }

        # Должно пройти без ошибок
        service.validate_connections(connections)

    def test_validate_connections_asymmetry_raises(self) -> None:
        """Нарушение симметрии должно вызывать ValueError."""
        cells_per_ring = [1, 4]
        service = PolarTopologyService(cells_per_ring)

        connections = {
            (0, 0): {(1, 0)},
            (1, 0): set(),  # Нет обратной связи
            (1, 1): set(),
            (1, 2): set(),
            (1, 3): set(),
        }

        with pytest.raises(ValueError):
            service.validate_connections(connections)

    def test_validate_connectivity(self) -> None:
        """Валидация должна проверять связность графа."""
        cells_per_ring = [1, 4]
        service = PolarTopologyService(cells_per_ring)

        # Связный граф
        connections = {
            (0, 0): {(1, 0)},
            (1, 0): {(0, 0), (1, 1)},
            (1, 1): {(1, 0), (1, 2)},
            (1, 2): {(1, 1), (1, 3)},
            (1, 3): {(1, 2)},
        }

        service.validate_connections(connections)

    def test_validate_isolated_raises(self) -> None:
        """Изолированные области должны вызывать ValueError."""
        cells_per_ring = [1, 4]
        service = PolarTopologyService(cells_per_ring)

        # Граф с изолированной ячейкой
        connections = {
            (0, 0): {(1, 0)},
            (1, 0): {(0, 0)},
            (1, 1): set(),  # Изолирована
            (1, 2): set(),
            (1, 3): set(),
        }

        with pytest.raises(ValueError):
            service.validate_connections(connections)

    def test_validate_cell_invalid_ring_raises(self) -> None:
        """Некорректное кольцо должно вызывать ValueError."""
        cells_per_ring = [1, 4]
        service = PolarTopologyService(cells_per_ring)

        with pytest.raises(ValueError):
            service.get_sector_bounds(5, 0)

    def test_validate_cell_invalid_sector_raises(self) -> None:
        """Некорректный сектор должен вызывать ValueError."""
        cells_per_ring = [1, 4]
        service = PolarTopologyService(cells_per_ring)

        with pytest.raises(ValueError):
            service.get_sector_bounds(1, 10)
