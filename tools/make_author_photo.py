import os, sys, requests
from PIL import Image

def fetch_image(url, tmp_path):
    r = requests.get(url, headers={'User-Agent': 'Mozilla/5.0'}, timeout=30)
    r.raise_for_status()
    with open(tmp_path, 'wb') as f:
        f.write(r.content)
    return tmp_path

def center_crop_to_ratio(im, target_ratio=0.8):
    w,h = im.size
    ratio = w/h if h>0 else 1
    if ratio > target_ratio + 1e-6:
        new_w = int(h*target_ratio)
        left = (w-new_w)//2
        return im.crop((left,0,left+new_w,h))
    elif ratio < target_ratio - 1e-6:
        new_h = int(w/target_ratio)
        top = (h-new_h)//2
        return im.crop((0,top,w,top+new_h))
    return im

def face_crop_heuristic(im, target_ratio=0.8):
    try:
        import cv2, numpy as np
        img = cv2.cvtColor(np.array(im), cv2.COLOR_RGB2BGR)
        gray = cv2.cvtColor(img, cv2.COLOR_BGR2GRAY)
        face_cascade = cv2.CascadeClassifier(cv2.data.haarcascades + 'haarcascade_frontalface_default.xml')
        faces = face_cascade.detectMultiScale(gray,1.1,5)
        if len(faces)>0:
            x,y,fw,fh = max(faces, key=lambda f:f[2]*f[3])
            w,h = im.size
            cy, cx = y+fh//2, x+fw//2
            tw,th = w,int(w/target_ratio)
            if th>h: th,tw = h,int(h*target_ratio)
            top = max(0, cy - int(th*0.4))
            left = max(0, cx - tw//2)
            top = min(top, h-th)
            left = min(left, w-tw)
            if left+tw>w: left=w-tw
            if top+th>h: top=h-th
            if left<0: left=0
            if top<0: top=0
            return im.crop((left,top,left+tw,top+th))
    except Exception:
        pass
    return center_crop_to_ratio(im, target_ratio)

def main():
    if len(sys.argv)<3:
        print('usage: python make_author_photo.py <image_url> <out_path>')
        return
    url, out = sys.argv[1], sys.argv[2]
    os.makedirs(os.path.dirname(out), exist_ok=True)
    tmp = out+'.tmp'
    fetch_image(url,tmp)
    im = Image.open(tmp).convert('RGB')
    im2 = face_crop_heuristic(im)
    im2 = im2.resize((120,150), Image.LANCZOS)
    im2.save(out, quality=90)
    print('saved', out, im2.size)
    try: os.remove(tmp)
    except: pass

if __name__=='__main__':
    main()
