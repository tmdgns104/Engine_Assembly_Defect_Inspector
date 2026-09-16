"""Global image quality only; no claim of per-slot visibility or product identity."""


def assess_image(image, config):
    import cv2
    gray = cv2.cvtColor(image, cv2.COLOR_BGR2GRAY)
    brightness = float(gray.mean())
    sharpness = float(cv2.Laplacian(gray, cv2.CV_64F).var())
    return {"valid": config["min_mean_brightness"] <= brightness <= config["max_mean_brightness"]
                     and sharpness >= config["min_blur_variance"],
            "mean_brightness": brightness, "laplacian_variance": sharpness,
            "scope": "global quality; not slot visibility verification"}
