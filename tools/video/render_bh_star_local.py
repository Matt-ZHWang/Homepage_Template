#!/usr/bin/env python3
"""Render a temporally coherent BH-star to AGN animation from keyframes.

The renderer combines bidirectional dense optical flow, a masked analytic
spiral/inflow field, and persistent advected gas tracers.  The first and last
frames are preserved exactly; procedural motion is strongest between them.
"""

from __future__ import annotations

import argparse
import math
import os
import subprocess
import sys
from pathlib import Path

# OpenCV is installed into a disposable local dependency directory for this
# renderer, keeping the website project itself free of Python package changes.
sys.path.insert(0, "/tmp/codex-video-deps")

import cv2
import numpy as np


WIDTH = 1280
HEIGHT = 720
FPS = 30
DURATION = 12.0
CENTER = np.array([WIDTH / 2.0, HEIGHT / 2.0], dtype=np.float32)


def smoothstep(x: float) -> float:
    x = float(np.clip(x, 0.0, 1.0))
    return x * x * (3.0 - 2.0 * x)


def smootherstep(x: float) -> float:
    x = float(np.clip(x, 0.0, 1.0))
    return x * x * x * (x * (x * 6.0 - 15.0) + 10.0)


def load_frame(path: Path) -> np.ndarray:
    image = cv2.imread(str(path), cv2.IMREAD_COLOR)
    if image is None:
        raise FileNotFoundError(path)
    h, w = image.shape[:2]
    target_ratio = WIDTH / HEIGHT
    ratio = w / h
    if ratio > target_ratio:
        crop_w = int(round(h * target_ratio))
        x0 = (w - crop_w) // 2
        image = image[:, x0 : x0 + crop_w]
    elif ratio < target_ratio:
        crop_h = int(round(w / target_ratio))
        y0 = (h - crop_h) // 2
        image = image[y0 : y0 + crop_h, :]
    return cv2.resize(image, (WIDTH, HEIGHT), interpolation=cv2.INTER_LANCZOS4)


def gas_mask(image: np.ndarray) -> np.ndarray:
    b, g, r = cv2.split(image.astype(np.float32))
    warm = np.clip((r - 0.72 * g - 0.24 * b - 8.0) / 105.0, 0.0, 1.0)
    brightness = np.clip((r + 0.35 * g - 34.0) / 185.0, 0.0, 1.0)
    mask = warm * brightness
    yy, xx = np.mgrid[0:HEIGHT, 0:WIDTH].astype(np.float32)
    radial = np.exp(-(((xx - CENTER[0]) / 565.0) ** 2 + ((yy - CENTER[1]) / 390.0) ** 2))
    mask *= radial
    mask = cv2.GaussianBlur(mask, (0, 0), 2.0)
    return np.clip(mask, 0.0, 1.0)


def dense_flow(a: np.ndarray, b: np.ndarray) -> np.ndarray:
    small_size = (WIDTH // 2, HEIGHT // 2)
    ga = cv2.cvtColor(cv2.resize(a, small_size), cv2.COLOR_BGR2GRAY)
    gb = cv2.cvtColor(cv2.resize(b, small_size), cv2.COLOR_BGR2GRAY)
    ga = cv2.GaussianBlur(ga, (0, 0), 1.1)
    gb = cv2.GaussianBlur(gb, (0, 0), 1.1)
    dis = cv2.DISOpticalFlow_create(cv2.DISOPTICAL_FLOW_PRESET_MEDIUM)
    dis.setFinestScale(1)
    dis.setGradientDescentIterations(45)
    flow = dis.calc(ga, gb, None)
    flow = cv2.resize(flow, (WIDTH, HEIGHT), interpolation=cv2.INTER_CUBIC)
    flow[..., 0] *= 2.0
    flow[..., 1] *= 2.0
    return flow.astype(np.float32)


YY, XX = np.mgrid[0:HEIGHT, 0:WIDTH].astype(np.float32)


def warp_forward(image: np.ndarray, flow: np.ndarray, amount: float) -> np.ndarray:
    map_x = XX - flow[..., 0] * amount
    map_y = YY - flow[..., 1] * amount
    return cv2.remap(
        image,
        map_x,
        map_y,
        interpolation=cv2.INTER_CUBIC,
        borderMode=cv2.BORDER_REFLECT101,
    )


def make_noise(seed: int) -> tuple[np.ndarray, np.ndarray]:
    rng = np.random.default_rng(seed)
    low_shape = (45, 80)
    nx = rng.normal(0.0, 1.0, low_shape).astype(np.float32)
    ny = rng.normal(0.0, 1.0, low_shape).astype(np.float32)
    nx = cv2.resize(nx, (WIDTH, HEIGHT), interpolation=cv2.INTER_CUBIC)
    ny = cv2.resize(ny, (WIDTH, HEIGHT), interpolation=cv2.INTER_CUBIC)
    nx = cv2.GaussianBlur(nx, (0, 0), 9.0)
    ny = cv2.GaussianBlur(ny, (0, 0), 9.0)
    norm = np.sqrt(nx * nx + ny * ny) + 1e-5
    return nx / norm, ny / norm


NOISE_A = make_noise(23)
NOISE_B = make_noise(91)


def add_fluid_advection(
    image: np.ndarray, segment_alpha: float, global_progress: float
) -> np.ndarray:
    envelope = math.sin(math.pi * float(np.clip(segment_alpha, 0.0, 1.0)))
    if envelope < 1e-4:
        return image

    dx = XX - CENTER[0]
    dy = YY - CENTER[1]
    radius = np.sqrt(dx * dx + dy * dy) + 1e-4
    tx, ty = -dy / radius, dx / radius
    rx, ry = -dx / radius, -dy / radius
    radial_weight = np.exp(-((radius / 475.0) ** 2))
    mask = gas_mask(image)

    # Persistent convection turns more slowly as the envelope is dispersed.
    swirl = (9.5 - 4.0 * global_progress) * envelope * radial_weight * mask
    inflow = 3.2 * (1.0 - 0.55 * global_progress) * envelope * radial_weight * mask

    phase = 2.0 * math.pi * (0.31 * global_progress)
    noise_x = math.cos(phase) * NOISE_A[0] + math.sin(phase) * NOISE_B[0]
    noise_y = math.cos(phase) * NOISE_A[1] + math.sin(phase) * NOISE_B[1]
    turbulence = 3.8 * envelope * mask

    disp_x = swirl * tx + inflow * rx + turbulence * noise_x
    disp_y = swirl * ty + inflow * ry + turbulence * noise_y

    map_x = XX - disp_x
    map_y = YY - disp_y
    return cv2.remap(
        image,
        map_x,
        map_y,
        interpolation=cv2.INTER_CUBIC,
        borderMode=cv2.BORDER_REFLECT101,
    )


class GasTracers:
    def __init__(self, start: np.ndarray, count: int = 1250) -> None:
        rng = np.random.default_rng(240821)
        mask = gas_mask(start)
        weights = np.power(mask, 1.7).ravel()
        weights /= weights.sum()
        chosen = rng.choice(weights.size, size=count, replace=True, p=weights)
        ys, xs = np.divmod(chosen, WIDTH)
        jitter = rng.uniform(-1.2, 1.2, (count, 2)).astype(np.float32)
        self.pos = np.column_stack((xs, ys)).astype(np.float32) + jitter
        self.prev = self.pos.copy()
        self.bias = rng.uniform(0.55, 1.0, count).astype(np.float32)

    def advance(self, progress: float, dt: float) -> None:
        self.prev[:] = self.pos
        rel = self.pos - CENTER
        radius = np.linalg.norm(rel, axis=1) + 1e-4
        unit = rel / radius[:, None]
        tangent = np.column_stack((-unit[:, 1], unit[:, 0]))

        swirl_speed = (42.0 - 17.0 * progress) * np.clip(1.25 - radius / 690.0, 0.18, 1.0)
        inward_speed = 10.5 * (1.0 - smoothstep(progress / 0.78))
        velocity = tangent * swirl_speed[:, None] - unit * inward_speed

        wind = smoothstep((progress - 0.46) / 0.45)
        vertical_sign = np.where(rel[:, 1] >= 0.0, 1.0, -1.0)
        velocity[:, 1] += vertical_sign * (24.0 * wind * self.bias)
        velocity[:, 0] += np.sign(rel[:, 0]) * (6.0 * wind * self.bias)

        self.pos += velocity.astype(np.float32) * dt
        self.pos[:, 0] = np.clip(self.pos[:, 0], 2.0, WIDTH - 3.0)
        self.pos[:, 1] = np.clip(self.pos[:, 1], 2.0, HEIGHT - 3.0)

    def composite(self, image: np.ndarray, progress: float) -> np.ndarray:
        mask = gas_mask(image)
        overlay = np.zeros_like(image, dtype=np.float32)
        valid_count = 0
        for i, (p0, p1) in enumerate(zip(self.prev, self.pos)):
            x, y = int(round(p1[0])), int(round(p1[1]))
            local = float(mask[y, x])
            if local < 0.13:
                continue
            color = image[y, x].astype(np.float32)
            color = np.clip(color * np.array([0.82, 1.03, 1.22], dtype=np.float32), 0, 255)
            strength = (0.18 + 0.16 * self.bias[i]) * min(1.0, local * 2.1)
            c = tuple(float(v * strength) for v in color)
            cv2.line(
                overlay,
                (int(round(p0[0])), int(round(p0[1]))),
                (x, y),
                c,
                1,
                cv2.LINE_AA,
            )
            valid_count += 1

        if valid_count == 0:
            return image
        glow = cv2.GaussianBlur(overlay, (0, 0), 1.25)
        mixed = image.astype(np.float32) + overlay * 0.62 + glow * 0.36
        return np.clip(mixed, 0, 255).astype(np.uint8)


def subtle_exposure_lock(image: np.ndarray, reference_luma: float) -> np.ndarray:
    gray = cv2.cvtColor(image, cv2.COLOR_BGR2GRAY)
    current = float(np.percentile(gray, 87.0)) + 1e-4
    gain = np.clip(reference_luma / current, 0.92, 1.08)
    return np.clip(image.astype(np.float32) * gain, 0, 255).astype(np.uint8)


def render(args: argparse.Namespace) -> None:
    key_paths = [Path(p) for p in args.keyframes]
    frames = [load_frame(p) for p in key_paths]
    times = np.asarray([0.0, 3.0, 6.0, 9.0, 11.2, DURATION], dtype=np.float32)
    if len(frames) != len(times):
        raise ValueError(f"Expected {len(times)} keyframes, got {len(frames)}")

    flows: list[tuple[np.ndarray, np.ndarray]] = []
    for index, (a, b) in enumerate(zip(frames[:-1], frames[1:])):
        print(f"Computing bidirectional flow {index + 1}/{len(frames) - 1}...", flush=True)
        flows.append((dense_flow(a, b), dense_flow(b, a)))

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
        f"{WIDTH}x{HEIGHT}",
        "-r",
        str(FPS),
        "-i",
        "-",
        "-an",
        "-c:v",
        "libx264",
        "-preset",
        "slow",
        "-crf",
        "17",
        "-pix_fmt",
        "yuv420p",
        "-movflags",
        "+faststart",
        str(args.output),
    ]
    encoder = subprocess.Popen(ffmpeg, stdin=subprocess.PIPE)
    assert encoder.stdin is not None

    tracers = GasTracers(frames[0])
    reference_luma = float(np.percentile(cv2.cvtColor(frames[0], cv2.COLOR_BGR2GRAY), 87.0))
    total_frames = int(round(DURATION * FPS))

    try:
        for frame_index in range(total_frames):
            time_s = frame_index / FPS
            progress = time_s / DURATION
            segment = int(np.searchsorted(times, time_s, side="right") - 1)
            segment = int(np.clip(segment, 0, len(frames) - 2))
            local = float((time_s - times[segment]) / (times[segment + 1] - times[segment]))
            eased = smootherstep(local)

            forward, backward = flows[segment]
            warped_a = warp_forward(frames[segment], forward, eased)
            warped_b = warp_forward(frames[segment + 1], backward, 1.0 - eased)
            base = cv2.addWeighted(warped_a, 1.0 - eased, warped_b, eased, 0.0)
            base = add_fluid_advection(base, local, progress)

            tracers.advance(progress, 1.0 / FPS)
            base = tracers.composite(base, progress)
            base = subtle_exposure_lock(base, reference_luma)

            # Preserve exact boundary frames.
            if frame_index == 0:
                base = frames[0]
            encoder.stdin.write(np.ascontiguousarray(base).tobytes())

            if frame_index % FPS == 0:
                print(f"Rendered {time_s:4.1f}/{DURATION:.1f}s", flush=True)
    finally:
        encoder.stdin.close()
        return_code = encoder.wait()
        if return_code != 0:
            raise RuntimeError(f"ffmpeg exited with status {return_code}")

    print(args.output)


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser()
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument("keyframes", nargs="+")
    return parser.parse_args()


if __name__ == "__main__":
    render(parse_args())
