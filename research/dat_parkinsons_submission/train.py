"""Entrant-local training only. Do not run this on hosted/retained competition data."""
from __future__ import annotations
import argparse, json, random
from dataclasses import asdict
from pathlib import Path
import numpy as np, pandas as pd, torch
from sklearn.metrics import log_loss, roc_auc_score
from sklearn.model_selection import StratifiedKFold, StratifiedGroupKFold
from torch import nn
from torch.utils.data import DataLoader, Dataset
from submission_src.datpark.bundle import save_bundle
from submission_src.datpark.model import DaTNet3d
from submission_src.datpark.preprocess import PreprocessConfig, load_and_preprocess
class ScanDataset(Dataset):
    def __init__(self, rows, nifti_dir: Path, config: PreprocessConfig, augment=False): self.rows=rows.reset_index(drop=True); self.nifti_dir=nifti_dir; self.config=config; self.augment=augment
    def __len__(self): return len(self.rows)
    def __getitem__(self,index):
        row=self.rows.iloc[index]; volume=load_and_preprocess(self.nifti_dir/f"{row.uid}.nii.gz",self.config); x=torch.from_numpy(volume)[None]
        if self.augment:
            for axis in (1,2,3):
                if torch.rand(())<.25: x=torch.flip(x,[axis])
            x=torch.clamp(x*(.90+.20*torch.rand(())),0,1)
        return x, torch.tensor(float(row.is_pathologic),dtype=torch.float32)
def seed_all(seed):
    random.seed(seed); np.random.seed(seed); torch.manual_seed(seed)
    if torch.cuda.is_available(): torch.cuda.manual_seed_all(seed)
def fit_temperature(logits,y):
    best=(float('inf'),1.0)
    for t in np.geomspace(.25,4.0,161):
        p=1/(1+np.exp(-np.clip(logits/t,-50,50))); loss=log_loss(y,p,labels=[0,1])
        if loss<best[0]: best=(loss,float(t))
    return best[1]
def run_epoch(model,loader,optimizer,device):
    training=optimizer is not None; model.train(training); criterion=nn.BCEWithLogitsLoss(); total=0.; outputs=[]; targets=[]
    for x,y in loader:
        x,y=x.to(device),y.to(device)
        with torch.set_grad_enabled(training):
            logits=model(x); loss=criterion(logits,y)
            if training: optimizer.zero_grad(set_to_none=True); loss.backward(); optimizer.step()
        total+=float(loss)*len(y); outputs.append(logits.detach().cpu().numpy()); targets.append(y.cpu().numpy())
    return total/max(1,len(loader.dataset)),np.concatenate(outputs),np.concatenate(targets)
def main():
    ap=argparse.ArgumentParser(); ap.add_argument('--labels',required=True); ap.add_argument('--nifti-dir',required=True); ap.add_argument('--out',required=True); ap.add_argument('--group-column'); ap.add_argument('--folds',type=int,default=5); ap.add_argument('--epochs',type=int,default=20); ap.add_argument('--batch-size',type=int,default=8); ap.add_argument('--seed',type=int,default=20260914); a=ap.parse_args(); seed_all(a.seed)
    labels=pd.read_csv(a.labels,dtype={'uid':str}); required={'uid','is_pathologic'}
    if not required.issubset(labels.columns): raise ValueError(f"labels must contain {sorted(required)}")
    if labels.uid.isna().any() or labels.uid.duplicated().any(): raise ValueError('uid must be unique and non-null')
    if not set(labels.is_pathologic.unique()).issubset({0,1}): raise ValueError('is_pathologic must be binary')
    y=labels.is_pathologic.to_numpy(dtype=np.int64)
    if a.group_column:
        if a.group_column not in labels.columns: raise ValueError('requested group column is absent')
        if labels[a.group_column].isna().any(): raise ValueError('group column contains null')
        split_iter=StratifiedGroupKFold(a.folds,shuffle=True,random_state=a.seed).split(labels,y,groups=labels[a.group_column].astype(str)); split_kind=f"StratifiedGroupKFold:{a.group_column}"
    else: split_iter=StratifiedKFold(a.folds,shuffle=True,random_state=a.seed).split(labels,y); split_kind='StratifiedKFold:NO_GROUP_AUTHORITY'
    config=PreprocessConfig(); device='cuda' if torch.cuda.is_available() else 'cpu'; out=Path(a.out); out.mkdir(parents=True,exist_ok=True); states=[]; temps=[]; fold_rows=[]
    for fold,(ti,vi) in enumerate(split_iter):
        seed_all(a.seed+fold); tr=DataLoader(ScanDataset(labels.iloc[ti],Path(a.nifti_dir),config,True),a.batch_size,shuffle=True,num_workers=4,pin_memory=torch.cuda.is_available()); va=DataLoader(ScanDataset(labels.iloc[vi],Path(a.nifti_dir),config,False),a.batch_size,shuffle=False,num_workers=4,pin_memory=torch.cuda.is_available()); model=DaTNet3d().to(device); opt=torch.optim.AdamW(model.parameters(),lr=2e-4,weight_decay=1e-3); best=None
        for _ in range(a.epochs):
            run_epoch(model,tr,opt,device); val_loss,logits,truth=run_epoch(model,va,None,device)
            if best is None or val_loss<best[0]: best=(val_loss,{k:v.detach().cpu().clone() for k,v in model.state_dict().items()},logits.copy(),truth.copy())
        _,state,logits,truth=best; temp=fit_temperature(logits,truth); prob=1/(1+np.exp(-np.clip(logits/temp,-50,50))); fold_rows.append({'fold':fold,'n':len(vi),'log_loss':log_loss(truth,prob,labels=[0,1]),'auc':roc_auc_score(truth,prob),'temperature':temp}); states.append(state); temps.append(temp)
    metadata={'seed':a.seed,'folds':a.folds,'split':split_kind,'fold_metrics':fold_rows,'preprocess':asdict(config),'claim':'participant-local validation only'}; save_bundle(out,states,temperatures=temps,preprocess=config,metadata=metadata); (out/'training_receipt.json').write_text(json.dumps(metadata,indent=2,sort_keys=True)+'\n'); print(json.dumps(metadata,indent=2,sort_keys=True))
if __name__=='__main__': main()
