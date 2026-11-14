from PIL import Image
import glob,sys
fs=sorted(glob.glob('preview/frame_*.jpg'),key=lambda f:float(f.split('_')[1][:-4]))
for k in range(0,len(fs),5):
  sub=fs[k:k+5]; sheet=Image.new('RGB',(540*len(sub),960))
  for i,f in enumerate(sub): sheet.paste(Image.open(f).resize((540,960)),(i*540,0))
  sheet.save(f'{sys.argv[1]}/sheet{k//5}.jpg',quality=85)
