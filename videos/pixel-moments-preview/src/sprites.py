"""Hand-drawn sprites (original) for the pixel-moments preview. '.' = transparent."""

# ---------------- Scene 1: dad sitting on the shelter bench ----------------
# H hair h hair-hi S skin s skin-shade d deep-shade g glasses l glint e eye
# B beard b beard-dark m mouth F fur f fur-dark J jacket j jacket-shade
# K jacket-hi T shirt t shirt-shade C cup c cup-shade L lid
# P jeans p jeans-shade Q jeans-hi X shoe x shoe-hi
DAD_HEAD = [
    ".....HHHHH.....",
    "...HHhhhHHHH...",
    "..HhhhHHHHHHH..",
    ".HHhHHHHHHHHHH.",
    ".HHHHHHHHHHHHH.",
    "HHHHHHHHHHHHHHH",
    "HHHHHSHHHHSSHHH",
    "HHHSSSSSSSSSSHH",
    ".HSSSSSSSSSSSH.",
    ".sSggggSggggSs.",
    ".sSglegglelgSs.",
    ".sSggggsggggSs.",
    ".sSSSSSssSSSSs.",
    "..SSSSSSdSSSSs.",
    "..BSSSSSSSSSBs.",
    "..BBBSmmmSBBB..",
    "...BBBBBBBBBb..",
    "....bBBBBBBb...",
    ".....bBBBBb....",
]
DAD_BODY = [
    "........FFFFFsSSsFFFFF........",
    "......FFFFFFFfTTfFFFFFFF......",
    "....JFFFFFFFfTTTTfFFFFFFFj....",
    "...JJJFFFFFfTTTTTTfFFFFFJjj...",
    "..JJJJJJJJjTTTTTTTTjJJJJJJjj..",
    "..JKJJJJJJjTTTTTTTTjJJJJJJjj..",
    ".JKKJJJJJJjTTTTTTTTjJJJJJJjjj.",
    ".JKJJJJJJJjTTTTTTTTjJJJJJJjjj.",
    ".JKJJJJJjjjTTTTTTTTjjJJJJJjjj.",
    ".JKJJJJjJJjTTTTTTTTjJjjJJJjjj.",
    ".JKJJJjJJJjTTTTTTTtjJJJjJJjjj.",
    ".JKJJJjJJJjTTTTTTTtjJJJjJJjjj.",
    ".JJJJjJJJJJTLLLLLtJJJJJJjJjjj.",
    "..JJjJJJJJSSCCCCCSSJJJJJJjjj..",
    "..JjJJJJJSSSCCCCcSSSJJJJJjj...",
    "...jJJJJJsSSCCCCcSSsJJJJjjj...",
    "...jjjjjjjsSCCCccSsjjjjjjjj...",
    "...PPPPPPPPPPPPPPPPPPPPPPPp...",
    "..QQPPPPPPPPPpPPPPPPPPPPPpp...",
    "..QPPPPPPPPPPpPPPPPPPPPPPpp...",
    "..pPPPPPPPPpp.pPPPPPPPPPpp....",
    "...pPPPPPPp....pPPPPPPPpp.....",
    "...QPPPPPPp....QPPPPPPPp......",
    "...QPPPPPPp....QPPPPPPPp......",
    "...QPPPPPPp....QPPPPPPPp......",
    "...QPPPPPPp....QPPPPPPPp......",
    "...QPPPPPPp....QPPPPPPPp......",
    "...pPPPPPPp....pPPPPPPPp......",
    "..XXXXXXXXX...XXXXXXXXXX......",
    ".XxxXXXXXXX..XxxXXXXXXXX......",
]
DAD_HEAD_X, DAD_HEAD_Y = 7, -18   # head offset relative to body (overlaps neck row)

# ---------------- Scene 1: kid in raincoat, sitting ----------------
# y coat Y coat-shade Z coat-deep H hair S skin s skin-shade e eye r cheek
# P pants p pants-shade R boot q boot-hi
KID_HEAD = [
    "...yyyyyy...",
    ".yyyyyyyyyy.",
    "yyyYYyyyyyyy",
    "yyYHHHHHHyyY",
    "yyHHHHHHHHyY",
    "yYHSSSHHSHyY",
    "yYSSSSSSSSyY",
    "yYSeSSSeSSYY",
    "yYrSSSSSrSYY",
    "yYsSSSsSSsYY",
    ".YYsSSSSsYY.",
    "..YYYYYYYY..",
]
KID_BODY = [
    "..yyyyyyyyy...",
    ".yyyyyyyyyyY..",
    "yyyyyyyyyyyYY.",
    "yyyYyyyyyyyYY.",
    "yyyYyyyyyyyYY.",
    "yyyYyyyyyyyYYY",
    "ySSYyyyyyyYSSY",
    ".ZZZZZZZZZZZZ.",
    ".PPPPPPPPPPPP.",
    ".PPPpPPPPpPPp.",
]
KID_LEGS = [  # dangling, two swing frames
    ["..PPp..PPp....",
     "..PPp..PPp....",
     "..PPp..PPp....",
     "..RRR..RRR....",
     ".RqRR..RqRR...",
     ".RRRR..RRRR..."],
    ["..PPp..PPp....",
     "..PPp..PPp....",
     "..RRR..PPp....",
     ".RqRR..RRR....",
     ".RRRR.RqRR....",
     "......RRRR...."],
]
KID_HEAD_X, KID_HEAD_Y = 1, -11

# ---------------- Scene 2: dad + kid from behind, holding hands ----------------
# H hair h hair-hi S skin s skin-shade g glasses-arm W shirt w shirt-shade v shirt-deep
# R shorts r shorts-shade
DADB_HEAD = [
    "....HHHHHH....",
    "..HHhhhHHHHH..",
    ".HHhhHHHHHHHH.",
    ".HhHHHHHHHHHH.",
    "HHHHHHHHHHHHHH",
    "HHHHHHHHHHHHHH",
    "sgHHHHHHHHHHgs",
    "SsHHHHHHHHHHsS",
    "sHHHHHHHHHHHHs",
    ".HHHHHHHHHHHH.",
    "..HHHHHHHHHH..",
    "...sSSSSSSs...",
    "...sSSSSSSs...",
]
DADB_BODY = [
    "....WWWWWWWWWWWWWWWWWW....",
    "..WWWWWWWWWWWWWWWWWWWWWW..",
    ".wWWWWWWWWWWWWWWWWWWWWWWw.",
    "wWWWWWWWWWWwwWWWWWWWWWWWWw",
    "wWWWWWWWWWWWwWWWWWWWWWWWWw",
    "wwWWWWWWWWWWwWWWWWWWWWWWww",
    "sWwWWWWWWWWWwWWWWWWWWWWwWs",
    "SwwWWWWWWWWWWwWWWWWWWWWwwS",
    "SswWWWWWWWWWWwWWWWWWWWWwsS",
    "SswWWWWWWWWWWwWWWWWWWWWwsS",
    "SswwWWWWWWWWWwWWWWWWWWwwsS",
    "SssvwWWWWWWWWwWWWWWWWwvssS",
    "SsSvwWWWWWWWWWwWWWWWWwvSsS",
    "SsS.wWWWWWWWWWwWWWWWWw.SsS",
    "SsS.wWWWWWWWWWwWWWWWWw.SsS",
    "SsS.wwWWWWWWWWwWWWWWww.SsS",
    ".SS.wwWWWWWWWWwWWWWWww.SS.",
    ".SS.vwWWWWWWWWWwWWWWwv.SS.",
    ".ss.vwwWWWWWWWWwWWWwwv.ss.",
    ".ss..vwwwWWWWWWwWWwwv..ss.",
    "..........................",
]
DADB_HEM = [
    ["....vwwwwwwwwwwwwwwwv.....",
     ".....v.vwwv.vwwv..v......."],
    [".....vwwwwwwwwwwwwwwwv....",
     "......v..vwwv..vwwv.v....."],
]
DADB_LEGS = [
    ".....RRRRRRRRRRRRRRRRr....",
    ".....RRRRRRRRrRRRRRRRr....",
    ".....RRRRRRRrrRRRRRRrr....",
    ".....rRRRRRRr.rRRRRRRr....",
    "......SSSSSs...sSSSSSs....",
    "......SSSSSs...sSSSSSs....",
    "......SSSSSs...SSSSSSs....",
    "......sSSSSs...SSSSSSs....",
    "......sSSSSs...SSSSSs.....",
    "......sSSSSs...SSSSSs.....",
    "......sSSSSs...sSSSSs.....",
    "......sSSSs....sSSSSs.....",
    "......sSSSs....sSSSSs.....",
    "......sSSSs....sSSSs......",
    "......sSSSs....sSSSs......",
    "......sSSSs....sSSSs......",
    ".....ssSSSs...ssSSSs......",
]
# kid from behind. K hair k hair-hi T tee t tee-shade U tee-deep P shorts p shorts-shade
KIDB_HEAD = [
    "...KkkKKK...",
    ".KKkkKKKKKK.",
    "KKkKKKKKKKKK",
    "KKKKKKKKKKKK",
    "sKKKKKKKKKKs",
    "SKKKKKKKKKKS",
    ".KKKKKKKKKK.",
    "..KKKKKKKK..",
    "...sSSSSs...",
]
KIDB_HAIR_WIND = [["k..........."], [".k.........."]]
KIDB_BODY = [
    "..TTTTTTTT..",
    ".TTTTTTTTTT.",
    "TTTTTTTTTTTt",
    "tTTTTTTTTTTt",
    "tTTTTTTTTTtt",
    "tTTTTTTTTTtt",
    ".UUUUUUUUUU.",
    ".PPPPPPPPPp.",
    ".PPPPppPPPp.",
    ".PPPp..PPPp.",
    "..SSs..SSs..",
    "..SSs..SSs..",
    "..SSs..SSs..",
    "..sSs..sSs..",
    "..sSs..sSs..",
    ".ssSs.ssSs..",
]
KIDB_ARM_DOWN = ["T", "S", "S", "S", "s", "S"]          # right arm hanging
KIDB_ARM_POINT = [                                     # right arm pointing up-right
    ["......SS",
     ".....SSs",
     "....SSs.",
     "...SSs..",
     "..TTs...",
     ".TT.....",
     "T......."],
    [".......S",
     "......SS",
     ".....SSs",
     "...SSs..",
     "..TTs...",
     ".TT.....",
     "T......."],
]
