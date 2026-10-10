#!/usr/bin/env python3
"""Create insight-led plots from the full raw-audit summaries and full Parquet table."""
from __future__ import annotations
import argparse, json, math
from pathlib import Path
import numpy as np
import pandas as pd
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt

ROOT=Path(__file__).resolve().parents[1]
DEFAULT_AUDIT=ROOT/"audit/raw_audit.json"
DEFAULT_FEATURES=ROOT/"data/processed/events.parquet"
DEFAULT_OUT=ROOT/"outputs/figures"


def save(fig,path):
    fig.tight_layout()
    fig.savefig(path,dpi=200,bbox_inches="tight")
    plt.close(fig)


def run(audit_path:Path,features:Path,outdir:Path):
    if not audit_path.is_file(): raise FileNotFoundError(f"Audit report missing: {audit_path}; run audit first")
    if not features.is_file(): raise FileNotFoundError(f"Parquet table missing: {features}; run ETL first")
    outdir.mkdir(parents=True,exist_ok=True)
    audit=json.loads(audit_path.read_text(encoding="utf-8"))
    q=audit["quality"]
    edges=np.asarray(q["pt_histogram_edges_GeV_as_documented"],dtype=float)
    rows=[]
    # 1. Object pT spectrum. Histogram counts were accumulated over every occupied slot.
    type_order=[("MET","MET"),("electron","Electrons"),("muon","Muons"),("jet","Jets")]
    counts=q["pt_histogram_counts_by_type"]
    under=q["pt_below_histogram_range_by_type"]
    over=q["pt_at_or_above_histogram_max_by_type"]
    display_labels=[f"<{edges[0]:g}"]+[f"{edges[i]:g}-{edges[i+1]:g}" for i in range(len(edges)-1)]+[f">={edges[-1]:g}"]
    x=np.arange(len(display_labels)); width=.19
    fig,ax=plt.subplots(figsize=(12,5.8))
    for i,(key,label) in enumerate(type_order):
        y=[int(under.get(key,0))]+list(counts[key])+[int(over.get(key,0))]
        ax.bar(x+(i-1.5)*width,y,width=width,label=label)
    ax.set_yscale("symlog",linthresh=1)
    ax.set_xticks(x,display_labels,rotation=45,ha="right")
    ax.set_xlabel("pT interval (GeV; metadata must confirm units)")
    ax.set_ylabel("Occupied object-slot count; symlog scale")
    ax.set_title("Full-file transverse-momentum distribution by object type")
    ax.legend(ncols=4); ax.grid(axis="y",alpha=.25)
    save(fig,outdir/"01_pt_spectrum_by_object_type.png")
    rows.append({"file":"01_pt_spectrum_by_object_type.png","data_basis":"all occupied tensor slots; exact streamed histogram counts","insight":"Compare kinematic scales across MET, electron, muon, jet; long tails and low-count bins remain visible."})

    # 2. Event object multiplicity distribution, counters generated from all tensor rows.
    m=q["multiplicity_distribution_by_event"]
    fig,axes=plt.subplots(1,3,figsize=(13.5,4.6))
    for ax,(key,label,color) in zip(axes,[("electron","Electrons per event","tab:blue"),("muon","Muons per event","tab:orange"),("jet","Jets per event","tab:green")]):
        kv=sorted(((int(k),int(v)) for k,v in m[key].items()),key=lambda z:z[0])
        xx=[v[0] for v in kv]; yy=[v[1] for v in kv]
        ax.bar(xx,yy,color=color,alpha=.88)
        ax.set_xlabel(label); ax.set_ylabel("Events")
        ax.set_xticks(range(min(xx,default=0),max(xx,default=0)+1))
        ax.tick_params(axis="x",rotation=0); ax.grid(axis="y",alpha=.22)
    fig.suptitle("Per-event reconstructed-object multiplicity; all events included",y=1.04)
    save(fig,outdir/"02_event_multiplicity.png")
    rows.append({"file":"02_event_multiplicity.png","data_basis":"exact full-file event-level counters","insight":"Shows occupancy patterns and whether fixed object-slot capacity creates concentration at upper multiplicities."})

    # 3 onwards use every event row from persisted feature Parquet.
    cols=["event_row_id","met_pt","met_phi","n_electrons","n_muons","n_jets","n_objects","leading_electron_pt","leading_muon_pt","leading_jet_pt","ht_jets","sum_lepton_pt","max_abs_eta","has_nonfinite","invalid_type_count","negative_pt_count","inconsistent_padding_count"]
    df=pd.read_parquet(features,columns=cols)
    if len(df) != int(audit["scan"]["rows_read"]):
        raise RuntimeError(f"Plot row count {len(df)} != full audit rows {audit['scan']['rows_read']}")
    n=len(df)

    # 3. HT versus MET joint density. Use full observed ranges, no percentile clipping.
    xx=df["met_pt"].to_numpy(dtype=float); yy=df["ht_jets"].to_numpy(dtype=float)
    xvalid=np.isfinite(xx); yvalid=np.isfinite(yy); both=xvalid&yvalid
    xmin=min(0.0,float(np.min(xx[both]))) if both.any() else 0.0
    ymin=min(0.0,float(np.min(yy[both]))) if both.any() else 0.0
    xmax=float(np.max(xx[both])) if both.any() else 1.0
    ymax=float(np.max(yy[both])) if both.any() else 1.0
    if xmax <= xmin: xmax=xmin+1
    if ymax <= ymin: ymax=ymin+1
    h,xe,ye=np.histogram2d(xx[both],yy[both],bins=(100,100),range=[[xmin,xmax],[ymin,ymax]])
    fig,ax=plt.subplots(figsize=(8.2,6.3))
    mesh=ax.pcolormesh(xe,ye,np.ma.masked_less_equal(h.T,0),norm=matplotlib.colors.LogNorm(vmin=1,vmax=max(1,float(h.max()))),cmap="viridis",shading="auto")
    cb=fig.colorbar(mesh,ax=ax);cb.set_label("Events per bin (log colour scale)")
    ax.set_xlabel("MET magnitude (dataset pT field; GeV if confirmed)")
    ax.set_ylabel(r"$H_T^{jets}=\sum p_T^{jet}$ (same units)")
    ax.set_title(f"Joint MET–jet activity density across {n:,} events")
    ax.text(.02,.98,f"Rows used: {int(both.sum()):,}; nonfinite pairs: {int((~both).sum()):,}",transform=ax.transAxes,va="top",color="white",bbox={"facecolor":"black","alpha":.55,"pad":4})
    save(fig,outdir/"03_met_vs_jet_ht_density.png")
    rows.append({"file":"03_met_vs_jet_ht_density.png","data_basis":f"all {n} rows; full finite observed axis range; 100x100 bins","insight":"Tests association between missing transverse momentum and scalar jet activity; density makes dominant regions and tails visible."})

    # 4. Exact quartiles for HT by jet multiplicity; full arrays, outlier symbols hidden only for legibility.
    groups=[df.loc[df.n_jets==k,"ht_jets"].to_numpy(dtype=float) for k in sorted(df.n_jets.unique())]
    labels=sorted(int(x) for x in df.n_jets.unique())
    fig,ax=plt.subplots(figsize=(10,5.7))
    ax.boxplot(groups,tick_labels=[str(x) for x in labels],showfliers=False,showmeans=True,meanline=True,patch_artist=False)
    ax.set_xlabel("Reconstructed jet multiplicity")
    ax.set_ylabel(r"$H_T^{jets}$ (sum of jet $p_T$)")
    ax.set_title("Jet activity conditional on jet multiplicity")
    ax.grid(axis="y",alpha=.25)
    ax.text(.99,.02,"Quartiles/means use all rows in each category; outlier markers hidden for readability.",ha="right",va="bottom",transform=ax.transAxes,fontsize=8)
    save(fig,outdir/"04_ht_by_jet_multiplicity.png")
    rows.append({"file":"04_ht_by_jet_multiplicity.png","data_basis":"exact pandas quartiles over every event; showfliers=False affects display only","insight":"Checks whether HT rises with object multiplicity and identifies broad or skewed conditional distributions."})

    # 5. Data-quality counts. Padding displayed separately because it is expected structure.
    flag_values={
        "Nonfinite events":int(df.has_nonfinite.sum()),
        "Invalid type events":int((df.invalid_type_count>0).sum()),
        "Negative-pT events":int((df.negative_pt_count>0).sum()),
        "Inconsistent-padding events":int((df.inconsistent_padding_count>0).sum()),
    }
    fig,ax=plt.subplots(figsize=(9.5,5.1))
    bars=ax.bar(list(flag_values),list(flag_values.values()))
    ax.set_ylabel("Events flagged; complete corpus")
    ax.set_title("Integrity flags; structural zero padding is audited separately")
    ax.tick_params(axis="x",rotation=18)
    ax.grid(axis="y",alpha=.25)
    for b,v in zip(bars,flag_values.values()): ax.text(b.get_x()+b.get_width()/2,v if v else 0, f"{v:,}",ha="center",va="bottom",fontsize=9)
    pad_pct=100*float(q["zero_padding_fraction"])
    ax.text(.99,.97,f"Zero-padded slots: {q['zero_padded_slots']:,}/{q['occupied_slots']+q['zero_padded_slots']:,} ({pad_pct:.1f}%)\nPadding is documented schema, not automatically an error.",transform=ax.transAxes,ha="right",va="top",fontsize=9,bbox={"facecolor":"white","alpha":.8,"edgecolor":"0.8"})
    save(fig,outdir/"05_data_quality_flags.png")
    rows.append({"file":"05_data_quality_flags.png","data_basis":"event-level flags across complete source file","insight":"Separates malformed values from expected structural padding. Zero counts are meaningful quality results."})

    # 6. Full-row correlations across interpretable engineered variables.
    corr_features=["met_pt","ht_jets","sum_lepton_pt","n_electrons","n_muons","n_jets","max_abs_eta"]
    corr=df[corr_features].corr(method="pearson")
    fig,ax=plt.subplots(figsize=(8,6.8))
    im=ax.imshow(corr.to_numpy(),vmin=-1,vmax=1,cmap="coolwarm",aspect="auto")
    ax.set_xticks(range(len(corr_features)),corr_features,rotation=45,ha="right")
    ax.set_yticks(range(len(corr_features)),corr_features)
    for i in range(len(corr_features)):
        for j in range(len(corr_features)):
            val=float(corr.iloc[i,j])
            ax.text(j,i,f"{val:.2f}",ha="center",va="center",fontsize=8,color="black")
    fig.colorbar(im,ax=ax,label="Pearson correlation")
    ax.set_title("Full-corpus event-feature correlation matrix")
    save(fig,outdir/"06_feature_correlations.png")
    rows.append({"file":"06_feature_correlations.png","data_basis":"Pearson coefficients computed from all Parquet event rows","insight":"Surfaces redundant engineered variables and correlations worth checking against event selection and detector physics."})

    # 7. Full-corpus jet-activity distribution; log1p transform improves visibility of the tail.
    ht=df["ht_jets"].to_numpy(dtype=float)
    ht=ht[np.isfinite(ht)]
    fig,ax=plt.subplots(figsize=(9,5.7))
    transformed=np.sign(ht)*np.log1p(np.abs(ht))
    ax.hist(transformed,bins=100,color="tab:blue",alpha=.88)
    ax.set_xlabel(r"$\mathrm{sign}(H_T)\log(1+|H_T|)$; all finite values")
    ax.set_ylabel("Events per bin")
    ax.set_title("Full-corpus jet-activity distribution on log1p scale")
    ax.grid(axis="y",alpha=.22)
    ax.text(.99,.97,f"Rows represented: {len(ht):,}; negative-HT flags remain listed in quality audit.",transform=ax.transAxes,ha="right",va="top",fontsize=8,bbox={"facecolor":"white","alpha":.8,"edgecolor":"0.8"})
    save(fig,outdir/"07_full_corpus_ht_distribution.png")
    rows.append({"file":"07_full_corpus_ht_distribution.png","data_basis":"all finite event-level HT values; signed-log rendering transform preserves negative values","insight":"Shows the full jet-activity distribution and its upper tail without event subsampling or clipping negative values."})

    # Optional plots appear only when the full-corpus clustering pass has completed.
    cluster_path=ROOT/"outputs/ml/cluster_scores.parquet"
    if cluster_path.is_file():
        scores=pd.read_parquet(cluster_path,columns=["event_row_id","cluster_id","centroid_distance","n_jets"])
        if len(scores)!=n: raise RuntimeError(f"ML score rows {len(scores)} != full data rows {n}")
        fig,ax=plt.subplots(figsize=(8.7,5.6))
        ax.hist(scores.centroid_distance.to_numpy(dtype=float),bins=100,color="tab:purple",alpha=.88)
        ax.set_xlabel("Standardized nearest-centroid Euclidean distance")
        ax.set_ylabel("Events")
        ax.set_title("Full-corpus clustering distance distribution")
        ax.text(.99,.97,"Exploratory feature-space distance; no calibrated signal probability.",transform=ax.transAxes,ha="right",va="top",fontsize=8,bbox={"facecolor":"white","alpha":.8,"edgecolor":"0.8"})
        save(fig,outdir/"08_cluster_distance_distribution.png")
        rows.append({"file":"08_cluster_distance_distribution.png","data_basis":"all event scores from complete-corpus clustering","insight":"Shows how concentrated the fitted feature-space distances are; tail points require physics and detector-quality review."})
        grp=[scores.loc[scores.n_jets==k,"centroid_distance"].to_numpy(dtype=float) for k in sorted(scores.n_jets.unique())]
        gl=[int(k) for k in sorted(scores.n_jets.unique())]
        fig,ax=plt.subplots(figsize=(9.5,5.5))
        ax.boxplot(grp,tick_labels=[str(k) for k in gl],showfliers=False,showmeans=True)
        ax.set_xlabel("Jet multiplicity");ax.set_ylabel("Nearest-centroid distance")
        ax.set_title("Clustering distance conditional on jet multiplicity")
        ax.text(.99,.02,"All scores contribute to quartiles; fliers hidden only in rendering.",transform=ax.transAxes,ha="right",va="bottom",fontsize=8)
        ax.grid(axis="y",alpha=.25)
        save(fig,outdir/"09_cluster_distance_by_jet_multiplicity.png")
        rows.append({"file":"09_cluster_distance_by_jet_multiplicity.png","data_basis":"exact quartiles using every scored event; outlier markers hidden only for readability","insight":"Tests whether apparent novelty scores depend strongly on reconstructed jet count."})
    manifest={"status":"COMPLETED_FULL_CORPUS_VISUALS","full_event_rows":int(n),"input_features":str(features.resolve()),"figures":rows,
              "method_note":"Figures 01-07 derive from whole-file counts or all event rows. Axis transforms, binning and box-plot rendering summarize values; analytics stages retain every row."}
    (outdir/"visual_manifest.json").write_text(json.dumps(manifest,indent=2),encoding="utf-8")
    print(json.dumps({"status":manifest["status"],"rows":n,"figures":[r["file"] for r in rows]},indent=2))
    return manifest


def main():
    ap=argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--audit",type=Path,default=DEFAULT_AUDIT)
    ap.add_argument("--features",type=Path,default=DEFAULT_FEATURES)
    ap.add_argument("--out",type=Path,default=DEFAULT_OUT)
    a=ap.parse_args();run(a.audit,a.features,a.out)
if __name__=="__main__":main()
