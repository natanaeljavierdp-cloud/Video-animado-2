import sys, numpy as np
sys.argv = [sys.argv[0], sys.argv[1]] + sys.argv[2:]
import video
from PIL import Image
ts = [float(x) for x in sys.argv[3].split(',')]
ims = [Image.fromarray(video.frame(int(t * 30))).resize((270, 480)) for t in ts]
cols = 8; rows = (len(ims) + cols - 1) // cols
sheet = Image.new('RGB', (270 * cols, 480 * rows))
for k, im in enumerate(ims): sheet.paste(im, ((k % cols) * 270, (k // cols) * 480))
sheet.save(sys.argv[2])
