import glob, sys
from PIL import Image
src, dst, tag = sys.argv[1], sys.argv[2], sys.argv[3]
fs = sorted(glob.glob(f"{src}/page*.png"))
for k in range(0, len(fs), 4):
    ims = [Image.open(f).convert("RGB") for f in fs[k:k+4]]
    w, h = ims[0].size
    sheet = Image.new("RGB", (w*len(ims) + 12*(len(ims)-1), h), "#777")
    for j, im in enumerate(ims):
        sheet.paste(im, (j*(w+12), 0))
    sheet.save(f"{dst}/{tag}_sheet{k//4+1}.png")
print(len(fs))
