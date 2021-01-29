"""
This module contains classes with tests for mozaik/stimuli/vision/topographica_based.py
"""

from mozaik.stimuli.vision.visual_stimulus import VisualStimulus
import imagen
import imagen.random
from imagen.transferfn import TransferFn
import param
from imagen.image import BoundingBox
import pickle
import numpy
from mozaik.tools.mozaik_parametrized import SNumber, SString
from mozaik.tools.units import cpd
from numpy import pi
from quantities import Hz, rad, degrees, ms, dimensionless
import mozaik.stimuli.vision.topographica_based as topo

import pytest

# Dummy class to get rid of NotImplementedError
class DummyTBVS(topo.TopographicaBasedVisualStimulus):
    def frames(self):
        return []


class TestTopographicaBasedVisualStimulus:
    def test_nontransparent(self):
        """
        Topographica stimuli do not handle transparency.
        """
        t = DummyTBVS(size_x=1, size_y=1, location_x=0.0, location_y=0.0)
        assert not t.transparent


class TopographicaBasedVisualStimulusTester(object):
    """
    Parent class containing convenience functions for testing stimulus generators in
    mozaik/stimuli/vision/topographica_based.py.
    """

    # Number of frames to test
    num_frames = 100
    # Default parameters for generating TopographicaBasedVisualStimuli frames
    default_topo = {
        "duration": 100,
        "frame_duration": 1,
        "background_luminance": 50.0,
        "density": 10.0,
        "location_x": 0.0,
        "location_y": 0.0,
        "size_x": 11.0,
        "size_y": 11.0,
    }

    def reference_frames(self, **params):
        """
        Generate or read frames to compare the output of TopographicaBasedVisualStimulus
        (or its child class) frames to. Parameters can be variable depending on child class
        and fixtures used.

        Returns
        -------
        Generator: tuple(numpy.array : frame, list : optional parameter(s), e.g. orientation))
        """
        raise NotImplementedError("Must be implemented by child class.")

    def topo_frames(self, **params):
        """
        Generate frames using TopographicaBasedVisualStimulus (or its child class) functions.

        Returns
        -------
        Generator: tuple(numpy.array : frame, list : optional parameter(s), e.g. orientation))
        """
        raise NotImplementedError("Must be implemented by child class.")

    def check_frames(self, **params):
        """
        Generate reference and TopographicaBased frames and check their equality.
        Check equivalence of reference frames and frames generated by
        topographica_based.py functions.
        """
        rf = self.reference_frames(**params)
        tf = self.topo_frames(**params)
        assert self.frames_equal(rf, tf, self.num_frames)

    def frames_equal(self, g0, g1, num_frames):
        """
        Checks if the first num_frames frames of the two generators are identical.
        """
        for i in range(num_frames):
            f0 = g0.next()
            f1 = g1.next()
            if not (numpy.array_equal(f0[0], f1[0]) and f0[1] == f1[1]):
                return False
        return True

    def test_frames(self, **params):
        """
        Function with a name that pytest will recognize. Use it to call compare_frames
        with the parameters passed from pytest.mark.parameterize to generate tests with
        unique names for each parameter combination. Must be implemented by child class.
        """
        pytest.skip("Must be implemented in child class and call check_frames.")


class TestNoise(TopographicaBasedVisualStimulusTester):

    experiment_seed = 0
    default_noise = {"grid_size": 11, "grid": False, "time_per_image": 2}

    @pytest.mark.parametrize("grid_size", [-1, 0, 0.9, 0.9999999999])
    def test_min_grid_size(self, grid_size):
        if type(self) == TestNoise:
            pytest.skip("Only run in child classes.")
        with pytest.raises(ValueError):
            self.check_frames(grid_size=grid_size)


# grid_size, size_x, grid, background_luminance, density
sparse_noise_params = [
    # Some basic parameter combinations
    (10, 10, True, 50, 5.0),
    (15, 15, False, 60, 6.0),
    (5, 5, False, 0.0, 15),
]


class TestSparseNoise(TestNoise):
    """
    Tests for the SparseNoise class.
    """

    def test_init_assert(self):
        """
        Checks the assertion in the init function of the class.
        """
        with pytest.raises(AssertionError):
            t = topo.SparseNoise(time_per_image=1.4, frame_duration=1.5)

    def reference_frames(
        self,
        grid_size=TestNoise.default_noise["grid_size"],
        size_x=TestNoise.default_topo["size_x"],
        grid=TestNoise.default_noise["grid"],
        background_luminance=TestNoise.default_topo["background_luminance"],
        density=TestNoise.default_topo["density"],
    ):

        time_per_image = self.default_noise["time_per_image"]
        frame_duration = self.default_topo["frame_duration"]
        aux = imagen.random.SparseNoise(
            grid_density=grid_size * 1.0 / size_x,
            grid=grid,
            offset=0,
            scale=2 * background_luminance,
            bounds=BoundingBox(radius=size_x / 2),
            xdensity=density,
            ydensity=density,
            random_generator=numpy.random.RandomState(seed=self.experiment_seed),
        )
        while True:
            aux2 = aux()
            for i in range(time_per_image / frame_duration):
                yield (aux2, [0])

    def topo_frames(
        self,
        grid_size=TestNoise.default_noise["grid_size"],
        size_x=TestNoise.default_topo["size_x"],
        grid=TestNoise.default_noise["grid"],
        background_luminance=TestNoise.default_topo["background_luminance"],
        density=TestNoise.default_topo["density"],
    ):
        snclass = topo.SparseNoise(
            grid_size=grid_size,
            grid=grid,
            background_luminance=background_luminance,
            density=density,
            size_x=size_x,
            size_y=self.default_topo["size_y"],
            location_x=self.default_topo["location_x"],
            location_y=self.default_topo["location_y"],
            time_per_image=self.default_noise["time_per_image"],
            frame_duration=self.default_topo["frame_duration"],
            experiment_seed=self.experiment_seed,
        )
        return snclass._frames

    @pytest.mark.parametrize(
        "grid_size, size_x, grid, background_luminance, density", sparse_noise_params
    )
    def test_frames(self, grid_size, size_x, grid, background_luminance, density):
        self.check_frames(
            grid_size=grid_size,
            size_x=size_x,
            grid=grid,
            background_luminance=background_luminance,
            density=density,
        )


# grid_size, size_x, background_luminance, density
dense_noise_params = [
    # Some basic parameter combinations
    (10, 10, 50, 5.0),
    (15, 15, 60, 6.0),
    (5, 5, 0.0, 15),
]


class TestDenseNoise(TestNoise):
    """
    Tests for the DenseNoise class.
    """

    def test_init_assert(self):
        """
        Checks the assertion in the init function of the class.
        """
        with pytest.raises(AssertionError):
            t = topo.DenseNoise(time_per_image=1.4, frame_duration=1.5)

    def reference_frames(
        self,
        grid_size=TestNoise.default_noise["grid_size"],
        size_x=TestNoise.default_topo["size_x"],
        background_luminance=TestNoise.default_topo["background_luminance"],
        density=TestNoise.default_topo["density"],
    ):
        time_per_image = TestNoise.default_noise["time_per_image"]
        frame_duration = TestNoise.default_topo["frame_duration"]
        aux = imagen.random.DenseNoise(
            grid_density=grid_size * 1.0 / size_x,
            offset=0,
            scale=2 * background_luminance,
            bounds=BoundingBox(radius=size_x / 2),
            xdensity=density,
            ydensity=density,
            random_generator=numpy.random.RandomState(seed=self.experiment_seed),
        )
        while True:
            aux2 = aux()
            for i in range(time_per_image / frame_duration):
                yield (aux2, [0])

    def topo_frames(
        self,
        grid_size=TestNoise.default_noise["grid_size"],
        size_x=TestNoise.default_topo["size_x"],
        background_luminance=TestNoise.default_topo["background_luminance"],
        density=TestNoise.default_topo["density"],
    ):
        snclass = topo.DenseNoise(
            grid_size=grid_size,
            grid=False,
            background_luminance=background_luminance,
            density=density,
            size_x=size_x,
            size_y=self.default_topo["size_y"],
            location_x=self.default_topo["location_x"],
            location_y=self.default_topo["location_y"],
            time_per_image=self.default_noise["time_per_image"],
            frame_duration=self.default_topo["frame_duration"],
            experiment_seed=self.experiment_seed,
        )
        return snclass._frames

    @pytest.mark.parametrize(
        "grid_size, size_x, background_luminance, density", dense_noise_params
    )
    def test_frames(self, grid_size, size_x, background_luminance, density):
        self.check_frames(
            grid_size=grid_size,
            size_x=size_x,
            background_luminance=background_luminance,
            density=density,
        )