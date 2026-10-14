import os, sys, requests
from PIL import Image

MODEL_URL = ('https://media.githubusercontent.com/media/opencv/opencv_zoo/main/'
             'models/face_detection_yunet/face_detection_yunet_2023mar.onnx')
MODEL_PATH = os.path.join(os.path.expanduser('~'), '.cache', 'naukal',
                          'face_detection_yunet_2023mar.onnx')


def fetch_image(url, tmp_path):
    r = requests.get(url, headers={'User-Agent': 'Mozilla/5.0'}, timeout=30)
    r.raise_for_status()
    with open(tmp_path, 'wb') as f:
        f.write(r.content)
    return tmp_path


def center_crop_to_ratio(im, target_ratio=0.8):
    w, h = im.size
    ratio = w / h if h > 0 else 1
    if ratio > target_ratio + 1e-6:
        new_w = int(h * target_ratio)
        left = (w - new_w) // 2
        return im.crop((left, 0, left + new_w, h))
    elif ratio < target_ratio - 1e-6:
        new_h = int(w / target_ratio)
        top = (h - new_h) // 2
        return im.crop((0, top, w, top + new_h))
    return im


def detect_face_box(im):
    """Самый крупный детект лица (OpenCV FaceDetectorYN, модель YuNet).

    Старый cv2.CascadeClassifier в OpenCV 5 убран, поэтому раньше поиск лица
    молча не срабатывал и фото резалось по центру. Модель скачивается один раз
    в кэш пользователя; без сети/OpenCV возвращаем None (тогда — центр-кроп).
    """
    try:
        import cv2
        import numpy as np
    except Exception:
        return None
    if not os.path.exists(MODEL_PATH):
        try:
            os.makedirs(os.path.dirname(MODEL_PATH), exist_ok=True)
            r = requests.get(MODEL_URL, timeout=60)
            r.raise_for_status()
            with open(MODEL_PATH, 'wb') as f:
                f.write(r.content)
        except Exception:
            return None
    try:
        img = cv2.cvtColor(np.array(im), cv2.COLOR_RGB2BGR)
        h, w = img.shape[:2]
        det = cv2.FaceDetectorYN.create(MODEL_PATH, '', (w, h), 0.6, 0.3, 5000)
        det.setInputSize((w, h))
        ok, faces = det.detect(img)
        if faces is None or len(faces) == 0:
            return None
        f = max(faces, key=lambda f: f[2] * f[3])
        return float(f[0]), float(f[1]), float(f[2]), float(f[3])
    except Exception:
        return None


def face_crop(im, box, target_ratio=0.8):
    """Плотный кадр «голова и плечи»: лицо по центру, ~40% высоты сверху."""
    x, y, fw, fh = box
    w, h = im.size
    crop_h = min(h, max(fh * 2.4, fh + fw * 1.2))
    crop_w = crop_h * target_ratio
    if crop_w > w:
        crop_w = w
        crop_h = crop_w / target_ratio
    cx, cy = x + fw / 2.0, y + fh / 2.0
    left = max(0.0, min(cx - crop_w / 2.0, w - crop_w))
    top = max(0.0, min(cy - crop_h * 0.40, h - crop_h))
    return im.crop((int(left), int(top), int(left + crop_w), int(top + crop_h)))


def make_crop(im, target_ratio=0.8):
    box = detect_face_box(im)
    if box:
        return face_crop(im, box, target_ratio)
    return center_crop_to_ratio(im, target_ratio)


def main():
    if len(sys.argv) < 3:
        print('usage: python make_author_photo.py <image_url> <out_path>')
        return
    url, out = sys.argv[1], sys.argv[2]
    os.makedirs(os.path.dirname(out), exist_ok=True)
    tmp = out + '.tmp'
    fetch_image(url, tmp)
    im = Image.open(tmp).convert('RGB')
    im2 = make_crop(im).resize((120, 150), Image.LANCZOS)
    im2.save(out, quality=90)
    print('saved', out, im2.size)
    try:
        os.remove(tmp)
    except Exception:
        pass


if __name__ == '__main__':
    main()
