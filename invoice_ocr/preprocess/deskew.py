from __future__ import annotations

import cv2
import numpy as np


def _rotate_bound(image: np.ndarray, angle_deg: float) -> np.ndarray:
    h, w = image.shape[:2]
    cx, cy = (w / 2.0, h / 2.0)
    matrix = cv2.getRotationMatrix2D((cx, cy), angle_deg, 1.0)

    cos = abs(matrix[0, 0])
    sin = abs(matrix[0, 1])

    new_w = int((h * sin) + (w * cos))
    new_h = int((h * cos) + (w * sin))

    matrix[0, 2] += (new_w / 2.0) - cx
    matrix[1, 2] += (new_h / 2.0) - cy

    return cv2.warpAffine(
        image,
        matrix,
        (new_w, new_h),
        flags=cv2.INTER_LINEAR,
        borderMode=cv2.BORDER_CONSTANT,
        borderValue=(255, 255, 255),
    )


def _estimate_angle_min_area_rect(image: np.ndarray) -> float:
    gray = cv2.cvtColor(image, cv2.COLOR_BGR2GRAY)
    bw = cv2.adaptiveThreshold(
        gray,
        255,
        cv2.ADAPTIVE_THRESH_GAUSSIAN_C,
        cv2.THRESH_BINARY_INV,
        31,
        15,
    )

    coords = np.column_stack(np.where(bw > 0))
    if coords.size == 0:
        return 0.0

    angle = cv2.minAreaRect(coords.astype(np.float32))[-1]
    if angle < -45:
        angle = 90 + angle
    elif angle > 45:
        angle = angle - 90

    return float(angle)


def deskew_image(
    image: np.ndarray,
    min_abs_angle: float = 0.7,
    max_abs_angle: float = 15.0,
) -> tuple[np.ndarray, dict]:
    angle = _estimate_angle_min_area_rect(image)
    meta = {
        "applied": False,
        "detected_angle_deg": round(angle, 4),
        "applied_angle_deg": 0.0,
        "method": "min_area_rect",
        "min_abs_angle_deg": min_abs_angle,
        "max_abs_angle_deg": max_abs_angle,
    }

    if abs(angle) < min_abs_angle or abs(angle) > max_abs_angle:
        return image, meta

    corrected = _rotate_bound(image, angle)
    meta["applied"] = True
    meta["applied_angle_deg"] = round(angle, 4)
    return corrected, meta
