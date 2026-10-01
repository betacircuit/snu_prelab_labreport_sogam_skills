#!/usr/bin/env python3
"""Conservative, reproducible measurement-photo correction; no reconstruction or OCR."""
from __future__ import annotations
import argparse
import hashlib
import json
from pathlib import Path
import numpy as np
from PIL import Image, ImageEnhance, ImageFilter, ImageOps


def sha256(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def rectify(image, points):
    p = np.asarray(points, dtype=float)
    if p.shape != (4, 2) or not np.isfinite(p).all():
        raise ValueError('screen needs four finite x,y pairs')
    if np.any(p < 0) or np.any(p[:,0] >= image.width) or np.any(p[:,1] >= image.height):
        raise ValueError('screen corners must be inside the oriented source image')
    edges = np.roll(p, -1, axis=0)-p
    cross = [edges[i,0]*edges[(i+1)%4,1]-edges[i,1]*edges[(i+1)%4,0] for i in range(4)]
    if any(c <= 0 for c in cross):
        raise ValueError('screen must be a convex clockwise quad: top-left, top-right, bottom-right, bottom-left')
    # Smaller opposing edge: do not pretend to create more measured detail.
    width = round(min(np.linalg.norm(p[1]-p[0]), np.linalg.norm(p[2]-p[3])))
    height = round(min(np.linalg.norm(p[3]-p[0]), np.linalg.norm(p[2]-p[1])))
    if min(width, height) < 16:
        raise ValueError('screen region is too small')
    destination = [(0,0), (width-1,0), (width-1,height-1), (0,height-1)]
    matrix, rhs = [], []
    for (x,y),(u,v) in zip(destination,p):
        matrix += [[x,y,1,0,0,0,-u*x,-u*y], [0,0,0,x,y,1,-v*x,-v*y]]
        rhs += [u,v]
    coefficients = np.linalg.solve(np.asarray(matrix), np.asarray(rhs))
    return image.transform((width,height), Image.Transform.PERSPECTIVE,
                           coefficients, Image.Resampling.BICUBIC)


def enhance(source, output, *, screen=None, crop=None, glare=.15, contrast=1.06, sharpen=60):
    source, output = Path(source).resolve(), Path(output).resolve()
    record = output.with_suffix(output.suffix + '.json')
    if source == output or output.exists() or record.exists():
        raise ValueError('use a new output path; original and existing results are never overwritten')
    if output.suffix.lower() != '.png':
        raise ValueError('output must be lossless .png')
    if not (0 <= glare <= .3 and .9 <= contrast <= 1.2 and 0 <= sharpen <= 100):
        raise ValueError('glare 0..0.3, contrast 0.9..1.2, sharpen 0..100 required')
    if screen is not None and crop is not None:
        raise ValueError('choose screen or crop, not both')
    before_hash = sha256(source)
    with Image.open(source) as original:
        image = ImageOps.exif_transpose(original).convert('RGB')
    source_size = image.size
    if screen is not None:
        image = rectify(image, screen)
    if crop is not None:
        x,y,w,h = crop
        if min(x,y) < 0 or min(w,h) <= 0 or x+w > image.width or y+h > image.height:
            raise ValueError('crop must be inside the source image')
        image = image.crop((x,y,x+w,y+h))
    if glare:
        # Remove only a small, smooth illumination variation. Occluded details stay occluded.
        rgb = np.asarray(image, dtype=np.float32)
        luminance = .2126*rgb[:,:,0] + .7152*rgb[:,:,1] + .0722*rgb[:,:,2]
        background = np.asarray(Image.fromarray(luminance.astype('uint8')).filter(
            ImageFilter.GaussianBlur(max(8, min(image.size)/12))), dtype=np.float32)
        corrected = np.clip(luminance-glare*(background-np.median(background)), 0, 255)
        scale = np.divide(corrected, np.maximum(luminance, 1))
        # A common RGB multiplier preserves channel hue; never recolor a trace independently.
        image = Image.fromarray(np.clip(rgb*scale[:,:,None], 0, 255).round().astype('uint8'))
    if contrast != 1:
        image = ImageEnhance.Contrast(image).enhance(contrast)
    if sharpen:
        image = image.filter(ImageFilter.UnsharpMask(radius=1, percent=sharpen, threshold=3))
    output.parent.mkdir(parents=True, exist_ok=True)
    image.save(output, format='PNG')
    assert sha256(source) == before_hash, 'source changed during correction'
    data = {'source':str(source), 'source_sha256':before_hash, 'output':str(output),
            'output_sha256':sha256(output), 'source_size':list(source_size), 'output_size':list(image.size),
            'operations':{'screen':screen,'crop':crop,'glare':glare,'contrast':contrast,'sharpen':sharpen},
            'review_status':'unreviewed',
            'limits':'No recovered digits or traces. Compare the original at 100% before report use.'}
    record.write_text(json.dumps(data, ensure_ascii=False, indent=2)+'\n', encoding='utf-8')
    return data


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('source', type=Path)
    parser.add_argument('--output', required=True, type=Path)
    parser.add_argument('--screen')
    parser.add_argument('--crop')
    parser.add_argument('--glare', type=float, default=.15)
    parser.add_argument('--contrast', type=float, default=1.06)
    parser.add_argument('--sharpen', type=int, default=60)
    args = parser.parse_args()
    try:
        screen = [list(map(float,p.split(','))) for p in args.screen.split(';')] if args.screen else None
        crop = list(map(int,args.crop.split(','))) if args.crop else None
        print(json.dumps(enhance(args.source,args.output,screen=screen,crop=crop,
                         glare=args.glare,contrast=args.contrast,sharpen=args.sharpen), ensure_ascii=False))
    except (ValueError, OSError, np.linalg.LinAlgError) as error:
        parser.exit(1, str(error)+'\n')


if __name__ == '__main__':
    main()
