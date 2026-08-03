# Restoration and Super Resolution

## Manual mode

Manual mode uses exactly the selected controls: upscale, deblur, denoise, artifact removal, and sharpening. Use this mode when visual inspection is more trustworthy than automatic ranking.

## Automatic mode

Automatic mode runs OCR on the original plus multiple restored paths. All attempts are shown. The highest reported OCR confidence is not treated as proof that the text is correct.

## AI mode

The optional AI backend uses OpenCV DNN Super Resolution when `opencv-contrib-python` and a compatible model file are configured. The project does not bundle a model. AI restoration may synthesize incorrect strokes and must not be treated as forensic recovery.

## Recommended workflow

1. Crop tightly with a margin.
2. Try the original image first.
3. Enable Manual restoration and inspect 2× output.
4. Try Automatic comparison if manual settings do not help.
5. Use AI restoration only as another comparison path.
6. Verify every character against the source.
