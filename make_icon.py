"""Generates pomodoro.ico - cute kawaii tomato icon."""
import struct, zlib, io, math

def make_tomato(size):
    try:
        from PIL import Image, ImageDraw, ImageFilter
    except ImportError:
        raise SystemExit("pip install pillow")

    img = Image.new("RGBA", (size, size), (0, 0, 0, 0))
    d = ImageDraw.Draw(img)
    s = size

    # Shadow
    shadow_img = Image.new("RGBA", (s, s), (0, 0, 0, 0))
    sd = ImageDraw.Draw(shadow_img)
    margin = int(s * 0.06)
    sd.ellipse([margin + int(s*0.03), margin + int(s*0.06),
                s - margin + int(s*0.03), s - margin + int(s*0.06)],
               fill=(0, 0, 0, 60))
    shadow_img = shadow_img.filter(ImageFilter.GaussianBlur(s * 0.04))
    img = Image.alpha_composite(img, shadow_img)
    d = ImageDraw.Draw(img)

    # Body gradient (hand-drawn with concentric ellipses)
    m = int(s * 0.08)
    body_colors = [
        (0,    (230, 50,  40,  255)),
        (0.15, (220, 45,  35,  255)),
        (0.35, (200, 35,  25,  255)),
        (0.55, (180, 25,  15,  255)),
        (0.75, (160, 18,  10,  255)),
        (1.0,  (140, 10,   5,  255)),
    ]
    for t, color in reversed(body_colors):
        shrink = int(t * m * 3)
        d.ellipse([m + shrink, m + shrink, s - m - shrink, s - m - shrink], fill=color)

    # Highlight (white sheen top-left)
    hl_x, hl_y = int(s * 0.28), int(s * 0.22)
    hl_rx, hl_ry = int(s * 0.15), int(s * 0.09)
    hl_img = Image.new("RGBA", (s, s), (0, 0, 0, 0))
    hd = ImageDraw.Draw(hl_img)
    hd.ellipse([hl_x - hl_rx, hl_y - hl_ry, hl_x + hl_rx, hl_y + hl_ry],
               fill=(255, 255, 255, 110))
    hl_img = hl_img.filter(ImageFilter.GaussianBlur(s * 0.025))
    img = Image.alpha_composite(img, hl_img)
    d = ImageDraw.Draw(img)

    # Stem
    stem_w = max(2, int(s * 0.07))
    stem_h = int(s * 0.18)
    stem_x = s // 2
    stem_top = int(s * 0.04)
    stem_bot = int(s * 0.22)
    d.rounded_rectangle(
        [stem_x - stem_w // 2, stem_top, stem_x + stem_w // 2, stem_bot],
        radius=stem_w // 2,
        fill=(60, 140, 50, 255)
    )

    # Leaf (left)
    leaf_pts_l = [
        (stem_x, int(s * 0.13)),
        (int(s * 0.28), int(s * 0.04)),
        (int(s * 0.32), int(s * 0.16)),
        (stem_x, int(s * 0.17)),
    ]
    d.polygon(leaf_pts_l, fill=(80, 170, 60, 230))

    # Leaf (right)
    leaf_pts_r = [
        (stem_x, int(s * 0.13)),
        (int(s * 0.72), int(s * 0.04)),
        (int(s * 0.68), int(s * 0.16)),
        (stem_x, int(s * 0.17)),
    ]
    d.polygon(leaf_pts_r, fill=(70, 155, 50, 230))

    # Eyes (kawaii dots)
    eye_y = int(s * 0.54)
    eye_r = max(2, int(s * 0.055))
    eye_gap = int(s * 0.14)
    cx = s // 2
    d.ellipse([cx - eye_gap - eye_r, eye_y - eye_r,
               cx - eye_gap + eye_r, eye_y + eye_r], fill=(50, 10, 5, 220))
    d.ellipse([cx + eye_gap - eye_r, eye_y - eye_r,
               cx + eye_gap + eye_r, eye_y + eye_r], fill=(50, 10, 5, 220))

    # Eye shine
    shine_r = max(1, int(eye_r * 0.4))
    for ex in [cx - eye_gap, cx + eye_gap]:
        d.ellipse([ex - shine_r + eye_r // 2, eye_y - eye_r + 2,
                   ex + shine_r + eye_r // 2, eye_y - eye_r + 2 + shine_r * 2],
                  fill=(255, 255, 255, 200))

    # Smile
    smile_w = int(s * 0.24)
    smile_y1 = int(s * 0.63)
    smile_y2 = int(s * 0.71)
    smile_thick = max(2, int(s * 0.04))
    d.arc([cx - smile_w, smile_y1, cx + smile_w, smile_y2 + smile_thick * 2],
          start=10, end=170, fill=(50, 10, 5, 200), width=smile_thick)

    # Cheeks (blush)
    blush_r = int(s * 0.09)
    blush_y = int(s * 0.62)
    blush_img = Image.new("RGBA", (s, s), (0, 0, 0, 0))
    bd = ImageDraw.Draw(blush_img)
    for bx in [cx - int(s * 0.22), cx + int(s * 0.22)]:
        bd.ellipse([bx - blush_r, blush_y - blush_r // 2,
                    bx + blush_r, blush_y + blush_r // 2],
                   fill=(255, 140, 130, 90))
    blush_img = blush_img.filter(ImageFilter.GaussianBlur(s * 0.03))
    img = Image.alpha_composite(img, blush_img)

    return img


def save_ico(path):
    sizes = [256, 64, 48, 32, 16]
    images = [make_tomato(s) for s in sizes]
    images[0].save(
        path, format="ICO",
        sizes=[(s, s) for s in sizes],
        append_images=images[1:]
    )
    print(f"Saved: {path}")


if __name__ == "__main__":
    save_ico("pomodoro.ico")
