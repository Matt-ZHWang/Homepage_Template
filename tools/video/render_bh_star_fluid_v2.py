#!/usr/bin/env python3
"""Render a continuous, fluid-like quasi-star to AGN transition.

Unlike the earlier keyframe/optical-flow renderer, this version never morphs
between a sequence of unrelated still images.  A single differential-rotation
field transports the gas throughout the shot, while the same field gradually
contracts and inclines the envelope into an edge-on accretion flow.  Persistent
advected tracers make the angular motion readable at native 60 fps.
"""

from __future__ import annotations

import argparse
import math
import subprocess
import sys
from pathlib import Path

sys.path.insert(0, "/tmp/codex-video-deps")

import cv2
import numpy as np


def clamp01(value: float | np.ndarray) -> float | np.ndarray:
    return np.clip(value, 0.0, 1.0)


def smoothstep(value: float | np.ndarray) -> float | np.ndarray:
    value = clamp01(value)
    return value * value * (3.0 - 2.0 * value)


def smootherstep(value: float | np.ndarray) -> float | np.ndarray:
    value = clamp01(value)
    return value**3 * (value * (value * 6.0 - 15.0) + 10.0)


def read_crop(path: Path, width: int, height: int) -> np.ndarray:
    image = cv2.imread(str(path), cv2.IMREAD_COLOR)
    if image is None:
        raise FileNotFoundError(path)
    source_h, source_w = image.shape[:2]
    target_ratio = width / height
    source_ratio = source_w / source_h
    if source_ratio > target_ratio:
        crop_w = int(round(source_h * target_ratio))
        left = (source_w - crop_w) // 2
        image = image[:, left : left + crop_w]
    elif source_ratio < target_ratio:
        crop_h = int(round(source_w / target_ratio))
        top = (source_h - crop_h) // 2
        image = image[top : top + crop_h, :]
    return cv2.resize(image, (width, height), interpolation=cv2.INTER_LANCZOS4)


def make_gas_masks(
    image: np.ndarray,
    xx: np.ndarray,
    yy: np.ndarray,
    opaque_envelope: bool = False,
) -> tuple[np.ndarray, np.ndarray, np.ndarray]:
    height, width = image.shape[:2]
    cx, cy = width * 0.5, height * 0.5
    b, g, r = cv2.split(image.astype(np.float32) / 255.0)
    warm = clamp01((r - 0.64 * g - 0.17 * b - 0.025) / 0.42)
    luminous = clamp01((r + 0.30 * g - 0.10) / 0.72)
    warm_gas = warm * np.power(luminous, 0.72)
    radius = np.sqrt(((xx - cx) / (0.48 * width)) ** 2 + ((yy - cy) / (0.55 * height)) ** 2)
    radial = np.exp(-np.power(radius, 3.0))
    # The final disk contains pale, nearly white emission that a red-only mask
    # would miss.  Restrict this brightness term to the central system.
    disk_radius = np.sqrt(((xx - cx) / (0.28 * width)) ** 2 + ((yy - cy) / (0.22 * height)) ** 2)
    pale_core = clamp01((r + g + b - 1.15) / 1.25) * np.exp(-disk_radius**2)
    bright = np.maximum(warm_gas * radial, pale_core)
    bright = cv2.GaussianBlur(bright.astype(np.float32), (0, 0), 1.6)
    bright = clamp01(bright * 1.28).astype(np.float32)

    # Very faint red material is still gas.  The original renderer discarded it
    # into the static star-field because it sat below the bright-emission cutoff.
    # Detect it from chromatic excess rather than absolute brightness, then let it
    # participate in a slower version of the same velocity field.
    red_excess = r - 0.58 * g - 0.20 * b
    faint_warm = smoothstep((red_excess - 0.006) / 0.105) * smoothstep((r - 0.012) / 0.115)
    broad_radius = np.sqrt(
        ((xx - cx) / (0.52 * width)) ** 2 + ((yy - cy) / (0.66 * height)) ** 2
    )
    broad_envelope = np.exp(-np.power(broad_radius, 3.2))
    faint = faint_warm * broad_envelope
    faint = cv2.GaussianBlur(faint.astype(np.float32), (0, 0), 2.4)
    # A soft skirt around bright filaments prevents stationary seams between the
    # fast and slow gas layers.
    filament_skirt = cv2.GaussianBlur(bright, (0, 0), 9.0) * 0.42
    all_gas = clamp01(np.maximum.reduce((bright, faint * 0.92, filament_skirt))).astype(np.float32)
    if opaque_envelope:
        envelope_radius = np.sqrt(
            ((xx - cx) / (0.43 * width)) ** 2 + ((yy - cy) / (0.47 * height)) ** 2
        )
        opaque_body = 1.0 - smoothstep((envelope_radius - 0.76) / 0.25)
        all_gas = np.maximum(all_gas, opaque_body.astype(np.float32) * 0.96)
    diffuse = clamp01(all_gas - bright).astype(np.float32)
    return bright, diffuse, all_gas


def fractal_noise(height: int, width: int, seed: int) -> np.ndarray:
    rng = np.random.default_rng(seed)
    result = np.zeros((height, width), np.float32)
    total = 0.0
    for grid_h, grid_w, amplitude in ((18, 32, 1.0), (36, 64, 0.55), (72, 128, 0.28)):
        noise = rng.normal(0.0, 1.0, (grid_h, grid_w)).astype(np.float32)
        noise = cv2.resize(noise, (width, height), interpolation=cv2.INTER_CUBIC)
        result += amplitude * noise
        total += amplitude
    result /= total
    result -= result.mean()
    result /= result.std() + 1e-5
    return np.clip(result / 2.8, -1.0, 1.0).astype(np.float32)


class FlowGeometry:
    def __init__(self, width: int, height: int) -> None:
        self.width = width
        self.height = height
        self.cx = width * 0.5
        self.cy = height * 0.5
        self.yy, self.xx = np.mgrid[0:height, 0:width].astype(np.float32)
        self.dx = self.xx - self.cx
        self.dy = self.yy - self.cy
        self.screen_radius = np.sqrt(self.dx * self.dx + self.dy * self.dy)
        self.noise_a = fractal_noise(height, width, 71)
        self.noise_b = fractal_noise(height, width, 113)
        self.noise_c = fractal_noise(height, width, 197)
        self.noise_d = fractal_noise(height, width, 251)

    def evolving_noise(self, seconds: float, rate: float = 0.23) -> tuple[np.ndarray, np.ndarray]:
        phase = seconds * rate * 2.0 * math.pi
        n1 = math.cos(phase) * self.noise_a + math.sin(phase) * self.noise_b
        phase2 = seconds * rate * 1.37 * 2.0 * math.pi + 0.8
        n2 = math.cos(phase2) * self.noise_c + math.sin(phase2) * self.noise_d
        return n1, n2

    def source_map(
        self,
        progress: float,
        seconds: float,
        rotation_scale: float = 1.0,
        rotation_speed: float = 1.0,
    ) -> tuple[np.ndarray, np.ndarray]:
        # The optically thick envelope hides most of its back side, so projected
        # rotation about the screen-vertical axis is represented as persistent
        # horizontal transport of the visible near-side gas.  This preserves the
        # horizontal equator without the folding artifacts of a spherical UV map.
        disk_cooling = smootherstep((progress - 0.12) / 0.70)
        contraction = 1.0 - 0.24 * smootherstep((progress - 0.04) / 0.78)
        vertical_contraction = 1.0 - 0.15 * disk_cooling
        volume_source_x = self.cx + self.dx / contraction
        volume_source_y = self.cy + self.dy / (contraction * vertical_contraction)

        # Turbulence should remain coherent even when the bulk rotation is very
        # fast, so its temporal rate is capped independently of orbital speed.
        noise_seconds = seconds * min(rotation_speed, 2.2)
        n1, n2 = self.evolving_noise(noise_seconds)
        inner_turbulence = np.exp(-np.power(self.screen_radius / (0.24 * self.width), 2.0))
        outer_turbulence = np.exp(
            -np.power((self.screen_radius - 0.34 * self.width) / (0.19 * self.width), 2.0)
        )
        # Keep the optically thick source artwork in one continuous sheet.  A
        # horizontal translation of this 2-D texture cannot represent the unseen
        # back side of a rotating sphere; holding the tiny engine fixed while the
        # envelope translated was what opened the equatorial seam.  Fast 3-D
        # rotation is instead carried by the depth-aware tracer layer below.
        central_axis_guard = smootherstep(self.screen_radius / (0.115 * self.width))
        map_x = volume_source_x
        map_y = volume_source_y
        turbulence_scale = 0.72 + 0.38 * rotation_scale
        motion_on = smootherstep(progress / 0.06)
        map_x += (
            5.5 * n2 * inner_turbulence * central_axis_guard
            + 13.0 * n1 * outer_turbulence
        ) * turbulence_scale * motion_on
        map_y += (
            4.0 * n1 * inner_turbulence * central_axis_guard
            + 9.5 * n2 * outer_turbulence
        ) * turbulence_scale * motion_on

        # A mild, coherent inclination prevents the optically thick equatorial
        # lane from reading as a horizontal cut.  The source plane eases into
        # the supplied AGN orientation as the target takes over.
        incline = math.radians(7.0) * (
            1.0 - float(smootherstep((progress - 0.34) / 0.44))
        )
        cos_i = math.cos(incline)
        sin_i = math.sin(incline)
        rel_map_x = map_x - self.cx
        rel_map_y = map_y - self.cy
        tilted_map_x = self.cx + cos_i * rel_map_x + sin_i * rel_map_y
        tilted_map_y = self.cy - sin_i * rel_map_x + cos_i * rel_map_y
        map_x = tilted_map_x
        map_y = tilted_map_y
        return map_x.astype(np.float32), map_y.astype(np.float32)

    def target_map(
        self,
        progress: float,
        seconds: float,
        rotation_scale: float = 1.0,
        rotation_speed: float = 1.0,
    ) -> tuple[np.ndarray, np.ndarray]:
        late = clamp01((progress - 0.50) / 0.50)
        radius_screen = self.screen_radius + 1e-4
        inner = np.exp(-np.power(radius_screen / (0.34 * self.width), 3.2))
        flatten = 0.24 * inner + 0.72 * (1.0 - inner)
        plane_x = self.dx
        plane_y = self.dy / flatten
        radius = np.sqrt(plane_x * plane_x + plane_y * plane_y) + 1e-4
        theta = np.arctan2(plane_y, plane_x)

        angular_weight = 0.22 + 0.78 * np.exp(-np.power(radius / (0.25 * self.width), 1.35))
        # The target enters pre-rotated and then travels forward into its supplied
        # orientation.  Therefore the last frame is not a distorted version of
        # the desired artwork: the map becomes exactly identity at the end.
        settle = smootherstep(late)
        rotation = -0.58 * (1.0 - settle) * angular_weight * rotation_scale
        noise_seconds = seconds * min(rotation_speed, 2.2)
        n1, n2 = self.evolving_noise(noise_seconds + 1.9, rate=0.18)
        turbulent_weight = np.exp(-np.power(radius / (0.44 * self.width), 2.0))
        remaining = 1.0 - settle
        theta_source = theta - rotation + 0.045 * n1 * turbulent_weight * remaining
        radius_source = radius * (1.0 + 0.026 * n2 * turbulent_weight * remaining)
        map_x = self.cx + radius_source * np.cos(theta_source)
        map_y = self.cy + flatten * radius_source * np.sin(theta_source)
        # The mature target disk is introduced small and buried, then grows to
        # its full radius while the BH-star envelope contracts and clears.
        disk_growth = smootherstep((progress - 0.25) / 0.62)
        disk_scale = 0.26 + 0.74 * disk_growth
        disk_zone = np.exp(-np.power(self.screen_radius / (0.17 * self.width), 4.0))
        small_disk_x = self.cx + (map_x - self.cx) / disk_scale
        small_disk_y = self.cy + (map_y - self.cy) / disk_scale
        map_x = map_x * (1.0 - disk_zone) + small_disk_x * disk_zone
        map_y = map_y * (1.0 - disk_zone) + small_disk_y * disk_zone

        # Once the disk is exposed, bright gas lanes repeatedly travel along
        # its horizontal plane.  This preserves the fixed vertical angular-
        # momentum axis while making several complete orbital passages visible.
        disk_stream_phase = seconds * 0.11 * rotation_speed * rotation_scale
        disk_stream_weight = (
            np.exp(-np.power(self.dy / (0.115 * self.height), 2.0))
            * np.exp(-np.power(self.dx / (0.31 * self.width), 4.0))
            * smootherstep((progress - 0.42) / 0.30)
        )
        stream_wave = np.sin(
            disk_stream_phase + self.dx / (0.046 * self.width) + 0.24 * n2
        )
        map_x += (8.0 + 10.0 * late) * stream_wave * disk_stream_weight
        map_y += 1.8 * np.cos(disk_stream_phase + self.dx / (0.060 * self.width)) * disk_stream_weight
        return map_x.astype(np.float32), map_y.astype(np.float32)


class TracerFlow:
    """Persistent particles with a decaying density trail, not flickering dots."""

    def __init__(self, mask: np.ndarray, count: int, trail_scale: float = 0.5) -> None:
        self.height, self.width = mask.shape
        self.cx, self.cy = self.width * 0.5, self.height * 0.5
        self.scale = trail_scale
        self.trail_w = int(round(self.width * trail_scale))
        self.trail_h = int(round(self.height * trail_scale))
        self.trail = np.zeros((self.trail_h, self.trail_w), np.float32)
        self.rng = np.random.default_rng(240821)
        self.inner_sink_radius = 0.012 * self.width
        yy, xx = np.mgrid[0 : self.height, 0 : self.width]
        rr = np.sqrt((xx - self.cx) ** 2 + (yy - self.cy) ** 2)
        # Keep only a tiny physical sink at the buried disk.  A broad zero-density
        # particle hole accumulates into an artificial dark circular silhouette.
        inner_feed = 0.22 + 0.78 * smoothstep(
            (rr - self.inner_sink_radius) / (0.045 * self.width)
        )
        weights = np.power(mask, 1.5) * inner_feed
        weights = weights.ravel().astype(np.float64)
        weights /= weights.sum()
        self.spawn_weights = weights
        self.pos = self._sample(count)
        self.depth = self._sample_depth(self.pos)
        self.energy = self.rng.uniform(0.35, 1.0, count).astype(np.float32)
        self.wind_class = self.rng.random(count) < 0.18

    def _sample(self, count: int) -> np.ndarray:
        chosen = self.rng.choice(self.spawn_weights.size, count, replace=True, p=self.spawn_weights)
        ys, xs = np.divmod(chosen, self.width)
        jitter = self.rng.uniform(-1.0, 1.0, (count, 2))
        return np.column_stack((xs, ys)).astype(np.float32) + jitter.astype(np.float32)

    def _sample_depth(self, position: np.ndarray) -> np.ndarray:
        nx = (position[:, 0] - self.cx) / (0.44 * self.width)
        ny = (position[:, 1] - self.cy) / (0.47 * self.height)
        available = np.sqrt(np.maximum(1.0 - nx * nx - ny * ny, 0.0))
        return (
            self.rng.uniform(-0.92, 0.92, position.shape[0]).astype(np.float32)
            * available.astype(np.float32)
            * (0.44 * self.width)
        )

    def advance(
        self,
        progress: float,
        seconds: float,
        dt: float,
        rotation_speed: float = 1.0,
    ) -> None:
        rel_x = self.pos[:, 0] - self.cx
        rel_y = self.pos[:, 1] - self.cy
        radius = np.sqrt(rel_x * rel_x + rel_y * rel_y + self.depth * self.depth) + 1e-4
        spin_up = 1.0 + 0.82 * float(smootherstep((progress - 0.08) / 0.74))
        angular_speed = (
            0.15 + 0.32 * np.exp(-np.power(radius / (0.30 * self.width), 1.3))
        ) * spin_up * rotation_speed
        velocity_x = angular_speed * self.depth
        velocity_y = np.zeros_like(velocity_x)
        velocity_depth = -angular_speed * rel_x
        # During the BH-star phase, gas orbits rapidly but remains a geometrically
        # thick envelope.  Strong early settling projected every orbit into the
        # same screen row and built an artificial equatorial bar.  Accretion
        # accelerates only after the inner disk begins to emerge.
        inward_speed = 3.5 + 12.0 * float(
            smootherstep((progress - 0.26) / 0.60)
        )
        velocity_x -= rel_x / radius * inward_speed
        velocity_y -= rel_y / radius * inward_speed
        velocity_depth -= self.depth / radius * inward_speed

        # Cooling contracts the existing equatorial structure vertically without
        # rotating its angular-momentum axis.
        cooling_envelope = float(smootherstep((progress - 0.34) / 0.46))
        velocity_y -= rel_y * (0.032 * cooling_envelope)

        # A minority of inner tracers feed the broad bipolar outflow after the
        # accretion disk is established; most continue orbiting and accreting.
        wind = float(smoothstep((progress - 0.63) / 0.28))
        launch = self.wind_class & (radius < 245.0)
        vertical_sign = np.where(rel_y >= 0.0, 1.0, -1.0)
        velocity_y[launch] += vertical_sign[launch] * (82.0 * wind)
        velocity_x[launch] *= 0.72

        # Coherent low-frequency turbulence bends streams without random jitter.
        phase = seconds * 0.72 * rotation_speed
        velocity_x += 7.0 * np.sin(phase + self.pos[:, 1] / 83.0)
        velocity_y += 5.5 * np.sin(phase * 1.21 + self.pos[:, 0] / 97.0)
        self.pos[:, 0] += velocity_x.astype(np.float32) * dt
        self.pos[:, 1] += velocity_y.astype(np.float32) * dt
        self.depth += velocity_depth.astype(np.float32) * dt

        rel = self.pos - np.array([self.cx, self.cy], np.float32)
        out = (
            (self.pos[:, 0] < 2.0)
            | (self.pos[:, 0] > self.width - 3.0)
            | (self.pos[:, 1] < 2.0)
            | (self.pos[:, 1] > self.height - 3.0)
            | (np.linalg.norm(rel, axis=1) < self.inner_sink_radius)
        )
        count = int(out.sum())
        if count:
            self.pos[out] = self._sample(count)
            self.depth[out] = self._sample_depth(self.pos[out])
            self.wind_class[out] = self.rng.random(count) < 0.18

    def render(self, dt: float, strength: float) -> np.ndarray:
        # Roughly a third of a second of history makes the velocity and curvature
        # legible while preserving fine turbulent structure.
        self.trail *= math.exp(-dt / 0.31)
        xs = np.clip((self.pos[:, 0] * self.scale).astype(np.int32), 0, self.trail_w - 1)
        ys = np.clip((self.pos[:, 1] * self.scale).astype(np.int32), 0, self.trail_h - 1)
        # Depth-dependent brightness supplies the missing spatial cue: gas is
        # bright on the near side, dims while orbiting behind the envelope, and
        # reappears at the opposite limb on every revolution.
        normalized_depth = np.clip(self.depth / (0.44 * self.width), -1.0, 1.0)
        near_side = 0.16 + 0.84 * smoothstep((normalized_depth + 0.30) / 0.95)
        np.add.at(self.trail, (ys, xs), self.energy * near_side * 0.31)
        visible = cv2.GaussianBlur(self.trail, (0, 0), 0.72)
        visible = cv2.resize(visible, (self.width, self.height), interpolation=cv2.INTER_CUBIC)
        visible = np.clip(visible * strength, 0.0, 1.0)
        return visible.astype(np.float32)


class BoundaryFlow:
    """Continuous accretion through the box edges plus a bipolar escape flow."""

    def __init__(
        self,
        width: int,
        height: int,
        inflow_count: int = 6800,
        outflow_count: int = 1900,
        trail_scale: float = 0.5,
    ) -> None:
        self.width = width
        self.height = height
        self.cx = width * 0.5
        self.cy = height * 0.5
        self.scale = trail_scale
        self.trail_w = int(round(width * trail_scale))
        self.trail_h = int(round(height * trail_scale))
        self.in_trail = np.zeros((self.trail_h, self.trail_w), np.float32)
        self.out_trail = np.zeros_like(self.in_trail)
        self.rng = np.random.default_rng(19082026)

        self.in_pos = self._spawn_inflow(inflow_count, fill_box=True)
        self.in_energy = self.rng.uniform(0.12, 0.68, inflow_count).astype(np.float32)
        self.in_phase = self.rng.uniform(0.0, 2.0 * math.pi, inflow_count).astype(np.float32)

        self.out_pos = np.empty((outflow_count, 2), np.float32)
        self.out_sign = np.empty(outflow_count, np.float32)
        self.out_energy = self.rng.uniform(0.16, 0.72, outflow_count).astype(np.float32)
        self.out_phase = self.rng.uniform(0.0, 2.0 * math.pi, outflow_count).astype(np.float32)
        self._respawn_outflow(np.ones(outflow_count, dtype=bool))

    def _spawn_inflow(self, count: int, fill_box: bool) -> np.ndarray:
        # Feed the envelope from all four boundaries.  Left/right remain
        # dominant, but a broader angular distribution prevents two opposing
        # streams from reading as one rigid equatorial bar.
        sides = self.rng.choice(4, count, p=[0.40, 0.40, 0.10, 0.10])
        boundary = np.empty((count, 2), np.float32)
        horizontal_gates = np.array([0.15, 0.32, 0.69, 0.86], np.float32)
        vertical_gates = np.array([0.16, 0.37, 0.67, 0.85], np.float32)

        left = sides == 0
        right = sides == 1
        top = sides == 2
        bottom = sides == 3
        for selection, x_value in ((left, -3.0), (right, self.width + 2.0)):
            n = int(selection.sum())
            if n:
                boundary[selection, 0] = x_value
                gates = self.rng.choice(horizontal_gates, n)
                boundary[selection, 1] = gates * self.height + self.rng.normal(0.0, 13.0, n)
        for selection, y_value in ((top, -3.0), (bottom, self.height + 2.0)):
            n = int(selection.sum())
            if n:
                boundary[selection, 1] = y_value
                gates = self.rng.choice(vertical_gates, n)
                boundary[selection, 0] = gates * self.width + self.rng.normal(0.0, 16.0, n)

        center = np.array([self.cx, self.cy], np.float32)
        if fill_box:
            fraction = self.rng.uniform(0.0, 0.93, (count, 1)).astype(np.float32)
            position = boundary * (1.0 - fraction) + center * fraction
            direction = center - boundary
            length = np.linalg.norm(direction, axis=1, keepdims=True) + 1e-4
            perpendicular = np.column_stack((-direction[:, 1], direction[:, 0])) / length
            bend = np.sin(math.pi * fraction[:, 0]) * self.rng.normal(
                0.0, 0.045 * self.width, count
            )
            position += perpendicular * bend[:, None]
            return position.astype(np.float32)
        return boundary.astype(np.float32)

    def _respawn_outflow(self, selection: np.ndarray) -> None:
        count = int(selection.sum())
        if count == 0:
            return
        self.out_pos[selection, 0] = self.cx + self.rng.normal(0.0, 34.0, count)
        self.out_pos[selection, 1] = self.cy + self.rng.normal(0.0, 7.0, count)
        self.out_sign[selection] = self.rng.choice(np.array([-1.0, 1.0], np.float32), count)

    def advance(
        self,
        progress: float,
        seconds: float,
        dt: float,
        rotation_speed: float = 1.0,
    ) -> None:
        center = np.array([self.cx, self.cy], np.float32)
        rel = self.in_pos - center
        radius = np.linalg.norm(rel, axis=1) + 1e-4
        inward = -rel / radius[:, None]
        inflow_speed = 58.0 + 24.0 * float(smootherstep((progress - 0.10) / 0.72))
        velocity = inward * inflow_speed
        # Large-scale coherent bends plus smaller moving eddies make the streams
        # clumpy and turbulent while preserving their net inward mass flux.
        velocity[:, 0] += 27.0 * np.sin(
            seconds * 0.73 * rotation_speed + self.in_pos[:, 1] / 71.0 + self.in_phase
        )
        velocity[:, 1] += 22.0 * np.sin(
            seconds * 0.91 * rotation_speed
            + self.in_pos[:, 0] / 89.0
            + self.in_phase * 0.71
        )
        velocity[:, 1] -= rel[:, 1] * (0.030 + 0.026 * progress)
        self.in_pos += velocity.astype(np.float32) * dt

        rel_after = self.in_pos - center
        # Boundary gas joins the optically thick envelope at its surface.  It
        # must not travel through the center, where left/right trails overlap
        # into an artificial straight band.  The merge radius contracts slowly
        # with the envelope as the AGN is exposed.
        merge_radius = self.width * (
            0.30 - 0.11 * float(smootherstep((progress - 0.15) / 0.70))
        )
        arrived = np.linalg.norm(rel_after, axis=1) < merge_radius
        escaped = (
            (self.in_pos[:, 0] < -8.0)
            | (self.in_pos[:, 0] > self.width + 8.0)
            | (self.in_pos[:, 1] < -8.0)
            | (self.in_pos[:, 1] > self.height + 8.0)
        )
        respawn = arrived | escaped
        count = int(respawn.sum())
        if count:
            self.in_pos[respawn] = self._spawn_inflow(count, fill_box=False)

        wind = float(smootherstep((progress - 0.42) / 0.30))
        out_rel = self.out_pos - center
        out_speed = 88.0 + 62.0 * wind
        out_velocity = np.zeros_like(self.out_pos)
        out_velocity[:, 1] = self.out_sign * out_speed
        out_velocity[:, 0] = (
            18.0
            * np.sin(
                seconds * 1.02 * rotation_speed
                + self.out_phase
                + out_rel[:, 1] / 118.0
            )
            + out_rel[:, 0] * 0.055
        )
        self.out_pos += out_velocity.astype(np.float32) * dt
        out_of_box = (
            (self.out_pos[:, 0] < -12.0)
            | (self.out_pos[:, 0] > self.width + 12.0)
            | (self.out_pos[:, 1] < -12.0)
            | (self.out_pos[:, 1] > self.height + 12.0)
        )
        self._respawn_outflow(out_of_box)

    def _deposit(self, field: np.ndarray, positions: np.ndarray, energy: np.ndarray) -> None:
        xs = np.clip((positions[:, 0] * self.scale).astype(np.int32), 0, self.trail_w - 1)
        ys = np.clip((positions[:, 1] * self.scale).astype(np.int32), 0, self.trail_h - 1)
        np.add.at(field, (ys, xs), energy * 0.055)

    def render(self, progress: float, dt: float) -> tuple[np.ndarray, np.ndarray]:
        self.in_trail *= math.exp(-dt / 0.34)
        self.out_trail *= math.exp(-dt / 0.31)
        self._deposit(self.in_trail, self.in_pos, self.in_energy)
        self._deposit(self.out_trail, self.out_pos, self.out_energy)

        inflow = cv2.GaussianBlur(self.in_trail, (0, 0), 0.76)
        inflow += cv2.GaussianBlur(self.in_trail, (0, 0), 2.5) * 0.22
        outflow = cv2.GaussianBlur(self.out_trail, (0, 0), 0.88)
        outflow += cv2.GaussianBlur(self.out_trail, (0, 0), 2.8) * 0.28
        inflow = cv2.resize(inflow, (self.width, self.height), interpolation=cv2.INTER_CUBIC)
        outflow = cv2.resize(outflow, (self.width, self.height), interpolation=cv2.INTER_CUBIC)
        inflow = np.clip(inflow * 0.48, 0.0, 1.0)
        wind_visibility = float(smoothstep((progress - 0.38) / 0.28))
        outflow = np.clip(outflow * 0.56 * wind_visibility, 0.0, 1.0)
        return inflow.astype(np.float32), outflow.astype(np.float32)


def remap(image: np.ndarray, map_x: np.ndarray, map_y: np.ndarray) -> np.ndarray:
    return cv2.remap(
        image,
        map_x,
        map_y,
        interpolation=cv2.INTER_CUBIC,
        borderMode=cv2.BORDER_CONSTANT,
        borderValue=0,
    )


def apply_site_palette(
    frame: np.ndarray, gas_mask: np.ndarray, screen_radius: np.ndarray
) -> np.ndarray:
    """Map warm orange emission to the site's red/cyan-on-black palette."""
    b, g, r = cv2.split(frame)
    emission = np.maximum.reduce((r, 0.82 * g, 0.58 * b))
    mid = smoothstep((emission - 0.06) / 0.48)[..., None]
    width = frame.shape[1]
    core_focus = np.exp(-np.power(screen_radius / (0.105 * width), 2.0))[..., None]
    hot = smoothstep((emission - 0.76) / 0.22)[..., None] * core_focus

    # BGR equivalents of the Project 01 page's #e3352a red, #8ccedf cyan,
    # #f6f0e8 ink, plus a dark crimson shadow color.
    deep_crimson = np.array([0.045, 0.010, 0.205], np.float32)
    site_red = np.array([0.125, 0.050, 0.790], np.float32)
    site_cyan = np.array([0.875, 0.808, 0.549], np.float32)
    site_ink = np.array([0.910, 0.941, 0.965], np.float32)
    hot_color = 0.88 * site_cyan + 0.12 * site_ink

    palette = deep_crimson * (1.0 - mid) + site_red * mid
    palette = palette * (1.0 - hot) + hot_color * hot
    brightness = np.power(np.clip(emission, 0.0, 1.0), 1.02)[..., None]
    recolored = brightness * palette * (0.79 + 0.22 * hot)
    strength = np.clip(gas_mask * 1.70, 0.0, 1.0)[..., None] * 0.94
    return frame * (1.0 - strength) + recolored * strength


def render(args: argparse.Namespace) -> None:
    width, height = args.width, args.height
    fps, duration = args.fps, args.duration
    geometry = FlowGeometry(width, height)
    start_u8 = read_crop(args.start, width, height)
    target_u8 = read_crop(args.target, width, height)
    start = start_u8.astype(np.float32) / 255.0
    target = target_u8.astype(np.float32) / 255.0
    source_bright, source_diffuse, source_mask = make_gas_masks(
        start_u8, geometry.xx, geometry.yy, opaque_envelope=True
    )
    target_bright, target_diffuse, target_mask = make_gas_masks(
        target_u8, geometry.xx, geometry.yy
    )

    # Removing the warm central emission leaves a stable star field beneath the
    # transported gas.  At t=0, gas + background reconstructs the source frame.
    source_background = start * (1.0 - source_mask[..., None])
    target_background = target * (1.0 - target_mask[..., None])
    tracers = TracerFlow(source_mask, args.particles, trail_scale=0.5)
    boundary_flow = BoundaryFlow(
        width,
        height,
        inflow_count=max(1200, int(args.particles * 0.38)),
        outflow_count=max(360, int(args.particles * 0.10)),
        trail_scale=0.5,
    )

    args.output.parent.mkdir(parents=True, exist_ok=True)
    ffmpeg = [
        "ffmpeg",
        "-y",
        "-v",
        "error",
        "-f",
        "rawvideo",
        "-pix_fmt",
        "bgr24",
        "-s",
        f"{width}x{height}",
        "-r",
        str(fps),
        "-i",
        "-",
        "-an",
        "-c:v",
        "libx264",
        "-preset",
        args.preset,
        "-crf",
        str(args.crf),
        "-pix_fmt",
        "yuv420p",
        "-movflags",
        "+faststart",
        str(args.output),
    ]
    encoder = subprocess.Popen(ffmpeg, stdin=subprocess.PIPE)
    assert encoder.stdin is not None

    render_duration = duration
    if args.render_seconds is not None:
        render_duration = min(duration, max(0.1, args.render_seconds))
    total_frames = int(round(render_duration * fps))
    dt = 1.0 / fps
    try:
        for frame_index in range(total_frames):
            seconds = frame_index / fps
            progress = seconds / duration
            source_x, source_y = geometry.source_map(
                progress,
                seconds,
                rotation_speed=args.rotation_speed,
            )
            source_slow_x, source_slow_y = geometry.source_map(
                progress,
                seconds,
                rotation_scale=0.70,
                rotation_speed=args.rotation_speed,
            )
            target_x, target_y = geometry.target_map(
                progress,
                seconds,
                rotation_speed=args.rotation_speed,
            )
            target_slow_x, target_slow_y = geometry.target_map(
                progress,
                seconds,
                rotation_scale=0.68,
                rotation_speed=args.rotation_speed,
            )

            moving_source = remap(start, source_x, source_y)
            moving_source_bright = remap(source_bright, source_x, source_y)
            moving_source_slow = remap(start, source_slow_x, source_slow_y)
            moving_source_diffuse = remap(source_mask, source_slow_x, source_slow_y)
            moving_target = remap(target, target_x, target_y)
            moving_target_bright = remap(target_bright, target_x, target_y)
            moving_target_slow = remap(target, target_slow_x, target_slow_y)
            moving_target_diffuse = remap(target_diffuse, target_slow_x, target_slow_y)

            reveal = float(smootherstep((progress - 0.42) / 0.43))
            disk_reveal = float(smootherstep((progress - 0.28) / 0.55))
            disk_zone = np.exp(
                -np.power(
                    (geometry.dx / (0.18 * width)) ** 2
                    + (geometry.dy / (0.10 * height)) ** 2,
                    2.0,
                )
            )
            local_reveal = reveal * (1.0 - disk_zone) + disk_reveal * disk_zone
            source_motion_detail = float(smootherstep(progress / 0.08))
            # Replace the envelope only where revealed target gas actually
            # covers it.  The previous oval-wide subtraction removed source gas
            # before the dim parts of the disk were composited, exposing the
            # black background as a long equatorial lane.
            target_coverage = np.maximum(moving_target_bright, moving_target_diffuse)
            source_replacement = reveal + (local_reveal - reveal) * target_coverage
            source_fast_alpha = (
                moving_source_bright
                * (1.0 - source_replacement)
                * 0.16
                * source_motion_detail
            )
            source_slow_alpha = moving_source_diffuse * (1.0 - source_replacement)
            target_fast_alpha = moving_target_bright * local_reveal
            target_slow_alpha = moving_target_diffuse * local_reveal

            background = source_background * (1.0 - reveal) + target_background * reveal
            frame = (
                background
                + moving_source * source_fast_alpha[..., None]
                + moving_source_slow * source_slow_alpha[..., None]
                + moving_target * target_fast_alpha[..., None]
                + moving_target_slow * target_slow_alpha[..., None]
            )

            # The early central engine stays hidden by the transported envelope
            # itself.  Avoid any circular center-only fog or blur—the geometric
            # boundary of such a patch reads as a premature black-hole sphere.
            tiny_glow = np.exp(
                -np.power(geometry.dx / (0.021 * width), 4.0)
                -np.power(geometry.dy / (0.008 * height), 4.0)
            ) * (1.0 - disk_reveal)
            frame += tiny_glow[..., None] * np.array([0.055, 0.035, 0.32], np.float32)

            # Enhance advected filaments rather than adding unrelated particles.
            gas_combined = np.maximum.reduce(
                (source_fast_alpha, source_slow_alpha, target_fast_alpha, target_slow_alpha)
            )
            soft = cv2.GaussianBlur(frame, (0, 0), 2.1)
            detail = frame - soft
            # Do not sharpen the buried center before the disk reveal: otherwise
            # a small dark minimum is exaggerated into an artificial black ball.
            center_detail_gate = 1.0 - np.exp(
                -np.power(geometry.screen_radius / (0.115 * width), 2.0)
            ) * (1.0 - disk_reveal)
            frame += detail * (0.40 * gas_combined[..., None] * center_detail_gate[..., None])

            tracers.advance(progress, seconds, dt, rotation_speed=args.rotation_speed)
            trail = tracers.render(dt, strength=0.92 + 0.30 * math.sin(math.pi * progress))
            final_settle = 1.0 - float(smoothstep((progress - 0.985) / 0.015))
            # Early on, the optically thick photosphere reprocesses and hides the
            # innermost tracer light.  The suppression is broad and smooth (never
            # a hard hole), then vanishes as the disk is exposed and grows.
            buried_center = 0.10 + 0.90 * smootherstep(
                geometry.screen_radius / (0.14 * width)
            )
            central_trail_gate = buried_center * (1.0 - disk_reveal) + disk_reveal
            trail *= (
                gas_combined
                * (0.75 + 0.25 * (1.0 - reveal))
                * final_settle
                * central_trail_gate
            )
            trail_color = np.array([0.06, 0.31, 1.00], np.float32)
            frame += trail[..., None] * trail_color * 0.62 * args.tracer_strength

            # Very gentle exposure breathing keeps the gas alive without flicker.
            pulse = 1.0 + 0.025 * math.sin(seconds * 1.17) + 0.012 * math.sin(seconds * 2.41 + 0.7)
            frame *= 1.0 + (pulse - 1.0) * gas_combined[..., None] * final_settle
            frame = apply_site_palette(frame, gas_combined, geometry.screen_radius)

            boundary_flow.advance(
                progress,
                seconds,
                dt,
                rotation_speed=args.rotation_speed,
            )
            inflow_streams, outflow_streams = boundary_flow.render(progress, dt)
            blood_red = np.array([0.095, 0.018, 0.640], np.float32)
            cool_core = np.array([0.780, 0.640, 0.390], np.float32)
            outflow_color = 0.86 * blood_red + 0.14 * cool_core
            stream_overlay = (
                inflow_streams[..., None] * blood_red * 0.34
                + outflow_streams[..., None] * outflow_color * 0.42
            ) * args.boundary_strength
            frame = 1.0 - (1.0 - frame) * (1.0 - np.clip(stream_overlay, 0.0, 0.82))
            frame = np.clip(frame, 0.0, 1.0)

            output = np.round(frame * 255.0).astype(np.uint8)
            encoder.stdin.write(np.ascontiguousarray(output).tobytes())
            if frame_index % fps == 0:
                print(f"Rendered {seconds:4.1f}/{duration:.1f}s", flush=True)
    finally:
        encoder.stdin.close()
        status = encoder.wait()
        if status != 0:
            raise RuntimeError(f"ffmpeg exited with status {status}")
    print(args.output)


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser()
    parser.add_argument("--start", type=Path, required=True)
    parser.add_argument("--target", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument("--width", type=int, default=1280)
    parser.add_argument("--height", type=int, default=720)
    parser.add_argument("--fps", type=int, default=60)
    parser.add_argument("--duration", type=float, default=12.0)
    parser.add_argument("--render-seconds", type=float)
    parser.add_argument("--rotation-speed", type=float, default=1.0)
    parser.add_argument("--particles", type=int, default=6200)
    parser.add_argument("--tracer-strength", type=float, default=1.0)
    parser.add_argument("--boundary-strength", type=float, default=1.0)
    parser.add_argument("--preset", default="slow")
    parser.add_argument("--crf", type=int, default=16)
    return parser.parse_args()


if __name__ == "__main__":
    render(parse_args())
