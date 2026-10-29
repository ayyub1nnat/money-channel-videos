import json, sys, numpy as np, soundfile as sf
SR=44100; tl=json.load(open("timeline.json")); D=tl["duration"]+0.2
v,sr=sf.read("voice.wav"); v=v.mean(1) if v.ndim>1 else v
if sr!=SR:
    import scipy.signal as ss; v=ss.resample_poly(v,SR,sr)
m,_=sf.read(sys.argv[1]); m=m.mean(1) if m.ndim>1 else m
N=int(D*SR); out=np.zeros(N); out[:min(N,len(v))]+=v[:N]
mm=np.pad(m[:N],(0,max(0,N-len(m[:N]))))
env=np.abs(np.pad(v,(0,max(0,N-len(v))))[:N]); k=int(0.15*SR); env=np.convolve(env,np.ones(k)/k,'same')
duck=np.where(env>0.01,float(sys.argv[2]),float(sys.argv[3])); duck=np.convolve(duck,np.ones(k)/k,'same')
out+=mm*duck
rng=np.random.default_rng(3)
def whoosh(t0,dur=0.35,g=0.2):
    n=int(dur*SR); x=rng.standard_normal(n); e=np.sin(np.linspace(0,np.pi,n))**2
    x=np.convolve(x,np.ones(30)/30,'same')*e*g; i=int(t0*SR); out[i:i+n]+=x[:max(0,N-i)]
def boom(t0,g=0.6):
    n=int(1.2*SR); tt=np.arange(n)/SR; x=np.sin(2*np.pi*(50-22*tt)*tt)*np.exp(-tt*3.5)*g; i=int(t0*SR); out[i:i+n]+=x[:max(0,N-i)]
boom(0.0,0.45); whoosh(0.85,0.3,0.22); boom(1.1,0.7)
for s in tl["scenes"][1:]: whoosh(max(0,s["start"]-0.15))
boom(tl["scenes"][5]["start"]+3.0,0.55)
out=out/max(1e-6,np.abs(out).max())*0.95
sf.write("mix.wav",out,SR); print("mix ok")
