"""Распаковщик блоков Clickteam (Click & Create / TGF, ~2000 г.).
Это обычный Deflate с тремя отличиями (выяснено по HCNSB.exe, sub_410470/410700/410D00/410E40):
  * заголовок блока 4 бита: биты 0-2 = тип (5=fixed, 6=dynamic, 7=stored), бит 3 = последний блок
  * порядок длин кодов в dynamic: [18,17,16,0,1,2,...,15]
  * в stored-блоке после выравнивания идёт только LEN (16 бит), без NLEN
"""
LBASE=[3,4,5,6,7,8,9,10,11,13,15,17,19,23,27,31,35,43,51,59,67,83,99,115,131,163,195,227,258]
LEXT=[0]*8+[1]*4+[2]*4+[3]*4+[4]*4+[5]*4+[0]
DBASE=[1,2,3,4,5,7,9,13,17,25,33,49,65,97,129,193,257,385,513,769,1025,1537,2049,3073,4097,6145,8193,12289,16385,24577]
DEXT=[0]*4+[x for x in range(1,14) for _ in (0,1)]
CL_ORDER=[18-i if i<3 else i-3 for i in range(19)]

class InflateError(Exception): pass

def _build(lens):
    maxb=max(lens) if lens else 0
    if maxb==0: return None,0
    cnt=[0]*(maxb+2)
    for l in lens: cnt[l]+=1
    cnt[0]=0
    code=0; nxt=[0]*(maxb+2)
    for b in range(1,maxb+1):
        code=(code+cnt[b-1])<<1; nxt[b]=code
    size=1<<maxb; table=[0]*size
    for sym,l in enumerate(lens):
        if not l: continue
        c=nxt[l]; nxt[l]+=1
        r=int(format(c,'0%db'%l)[::-1],2)
        v=(sym<<4)|l
        for i in range(r,size,1<<l): table[i]=v
    return table,maxb

_FIXED=None
def _fixed():
    global _FIXED
    if _FIXED is None:
        ll=[8]*144+[9]*112+[7]*24+[8]*8
        _FIXED=(_build(ll),_build([5]*30))
    return _FIXED

def inflate(data, expected=None, want_pos=False):
    pos=0; buf=0; cnt=0; n=len(data); out=bytearray()
    def need(k):
        nonlocal pos,buf,cnt
        if pos>n+8: raise InflateError('данные кончились')
        while cnt<k:
            b=data[pos] if pos<n else 0
            pos+=1; buf|=b<<cnt; cnt+=8
    def bits(k):
        nonlocal buf,cnt
        if k==0: return 0
        need(k); v=buf&((1<<k)-1); buf>>=k; cnt-=k; return v
    def sym(t):
        nonlocal buf,cnt
        table,mb=t
        if table is None: raise InflateError('empty table')
        need(mb); v=table[buf&((1<<mb)-1)]; l=v&15
        if l==0: raise InflateError('bad code')
        buf>>=l; cnt-=l; return v>>4
    while True:
        h=bits(4); typ=h&7; final=h>>3
        if typ==7:
            drop=cnt&7; buf>>=drop; cnt-=drop
            ln=bits(16)
            for _ in range(ln): out.append(bits(8))
        elif typ in (5,6):
            if typ==5: lt,dt=_fixed()
            else:
                hlit=bits(5)+257; hdist=bits(5)+1; hclen=bits(4)+4
                if hlit>286 or hdist>30: raise InflateError('bad counts')
                cl=[0]*19
                for i in range(hclen): cl[CL_ORDER[i]]=bits(3)
                ct=_build(cl); lens=[]; prev=0
                while len(lens)<hlit+hdist:
                    s=sym(ct)
                    if s<16: lens.append(s); prev=s
                    elif s==16:
                        r=bits(2)+3; lens+= [prev]*r
                    elif s==17:
                        r=bits(3)+3; lens+=[0]*r; prev=0
                    else:
                        r=bits(7)+11; lens+=[0]*r; prev=0
                if len(lens)>hlit+hdist: raise InflateError('overrun')
                lt=_build(lens[:hlit]); dt=_build(lens[hlit:])
            while True:
                s=sym(lt)
                if expected is not None and len(out)>expected: raise InflateError('вывод больше ожидаемого')
                if s<256: out.append(s)
                elif s==256: break
                else:
                    s-=257
                    if s>=29: raise InflateError('bad length sym')
                    ln=LBASE[s]+bits(LEXT[s])
                    d=sym(dt)
                    if d>=30: raise InflateError('bad dist sym')
                    dist=DBASE[d]+bits(DEXT[d])
                    if dist>len(out): raise InflateError('dist too far')
                    st=len(out)-dist
                    if dist>=ln: out+=out[st:st+ln]
                    else:
                        for i in range(ln): out.append(out[st+i])
        else:
            raise InflateError('bad block type %d'%typ)
        if expected is not None and len(out)>expected: raise InflateError('вывод больше ожидаемого')
        if final: break
    if want_pos:
        return bytes(out), pos - cnt // 8
    return bytes(out)
