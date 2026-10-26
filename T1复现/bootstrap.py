"""Use local / previous task numerical packages; no upstream files are modified."""
import os,sys,pathlib,runpy
ROOT=pathlib.Path(__file__).resolve().parent
for p in [ROOT.parent/'A1复现/vendor',ROOT/'vendor']:
 if p.exists():sys.path.insert(0,str(p))
for k in ['OPENBLAS_NUM_THREADS','MKL_NUM_THREADS','OMP_NUM_THREADS']:os.environ[k]='1'
os.environ['MPLCONFIGDIR']=str(ROOT/'results/mplconfig')
script=sys.argv[1];sys.argv=sys.argv[1:];sys.path.insert(0,str(pathlib.Path(script).resolve().parent));runpy.run_path(script,run_name='__main__')
