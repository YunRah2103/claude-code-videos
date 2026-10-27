import os
from PIL import Image
OUT=os.path.dirname(os.path.abspath(__file__))
W,H,S=36,56,12
im=Image.new("RGBA",(W,H),(0,0,0,0)); px=im.load()
def r(x0,y0,x1,y1,c):
    for y in range(y0,y1+1):
        for x in range(x0,x1+1): px[x,y]=c
C=lambda *a:a+(255,)
HR=C(34,26,28);HL=C(78,62,68);SK=C(190,136,98);SH=C(158,108,76);CK=C(208,144,114);WH=C(255,255,255)
GL=C(196,202,212);BK=C(20,20,30);MO=C(110,50,50);FL=C(70,70,76);FD=C(52,52,58);TE=C(172,172,184)
PA=C(38,70,83);SO=C(240,240,240)
# head (rounded)
r(9,7,26,24,SK);r(10,6,25,6,SK);r(10,25,25,25,SK)
r(9,12,9,22,SH);r(26,12,26,22,SH);r(8,16,8,20,SK);r(27,16,27,20,SK)   # sides + ears
# hair: tidy swoop, forehead visible on left, fringe sweeps right
r(10,2,25,5,HR);r(8,4,27,8,HR);r(8,9,9,14,HR);r(26,9,27,14,HR)
r(19,9,25,10,HR);r(22,11,25,11,HR);r(10,9,13,9,HR);r(10,10,11,10,HR)
r(13,3,17,5,HL);r(20,3,23,4,HL);px[14,1]=HR;px[18,1]=HR;px[21,2]=HR
# brows
r(11,12,15,12,HR);r(20,12,24,12,HR)
# glasses
for x0 in(10,19):
    r(x0,13,x0+6,19,GL);r(x0+1,14,x0+5,18,SK)
    r(x0+2,15,x0+3,17,BK);px[x0+2,15]=WH;px[x0+1,15]=WH;px[x0+1,16]=WH
r(17,14,18,14,GL)
# nose, cheeks, smile
r(17,20,18,21,SH);r(11,21,12,21,CK);r(23,21,24,21,CK)
px[14,22]=MO;r(15,23,20,23,MO);px[21,22]=MO;r(16,24,19,24,SK)
# neck
r(15,26,20,27,SH)
# plain white tee
TW=C(255,255,255);TS=C(222,226,234);JN=C(78,108,156);JD=C(56,82,128);JL=C(100,132,182)
r(10,28,25,43,TW);r(14,28,21,29,SH);r(16,28,19,29,SH)
r(10,28,10,43,TS);r(25,28,25,43,TS);r(10,42,25,43,TS)
r(5,29,9,35,TW);r(26,29,30,35,TW);r(5,35,9,35,TS);r(26,35,30,35,TS)
r(5,36,9,44,SK);r(26,36,30,44,SK);r(5,36,5,44,SH);r(30,36,30,44,SH)
# baggy jeans (wider than torso) + white shoes
r(8,44,27,53,JN);r(17,48,18,53,(0,0,0,0))
r(8,44,27,45,JD);r(9,47,11,52,JD);r(24,47,26,52,JD);r(13,46,15,51,JL);r(20,46,22,51,JL)
r(8,52,16,53,JD);r(19,52,27,53,JD)
r(9,54,16,55,SO);r(19,54,26,55,SO);r(9,55,16,55,C(200,205,215));r(19,55,26,55,C(200,205,215))
out=Image.new("RGBA",(W,H),(0,0,0,0));o=out.load();OL=C(27,27,47)
for y in range(H):
    for x in range(W):
        if px[x,y][3]==0:
            for dx,dy in((1,0),(-1,0),(0,1),(0,-1)):
                a,b=x+dx,y+dy
                if 0<=a<W and 0<=b<H and px[a,b][3]: o[x,y]=OL;break
out.alpha_composite(im)
big=out.resize((W*S,H*S),Image.NEAREST)
big.save(OUT+"/yunus.png")
bg=Image.new("RGBA",big.size,(255,255,255,255));bg.alpha_composite(big)
bg.convert("RGB").save(OUT+"/yunus_preview.png")
out.save(OUT+"/yunus_1x.png")
